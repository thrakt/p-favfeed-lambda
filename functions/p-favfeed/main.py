import json
import logging
import os
import re
import hashlib

from datetime import datetime

import requests

import boto3
from boto3.dynamodb.conditions import Key, Attr

from requests.exceptions import Timeout

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handle(event, context):
    """
    Lambda handler
    """

    json = get_json(get_access_token()) or get_json(reflesh_access_token())

    if not json:
        return "none"

    latest = json[0]["id"]
    if not latest == get_latest():
        logger.info("found new item")
        update_latest(latest)
        notify_push()

    return return_feed(json)


def get_json(accessToken):
    logger.info("getting json")
    json = requests.get(
        os.environ["JSON_API_URL"],
        headers={
            "Authorization": "Bearer " + accessToken
        },
        timeout=2
    ).json()
    if not json["status"] == "success":
        logger.info("failed to get json")
        return None

    return json["response"]


def notify_push():
    logger.info("notify PuSH")
    requests.post(
        "https://pubsubhubbub.appspot.com/publish",
        {
            "hub.mode": "publish",
            "hub.url": "https://"+os.environ["HOST"]+"/feed/"
        }
    )


def return_feed(json):
    logger.info("convert to feed")

    first_item = json[0]
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>P Favorite User's Picture Feed for {name}</title>
<link href="{link_url}"/>
<link type="application/atom+xml" rel="self" href="https://{host}/feed/"/>
<link rel="hub" href="http://pubsubhubbub.appspot.com"/>
<summary>P Favorite User's Picture Feed for {name}</summary>
<updated>{updated}</updated>
<id>https://{host}/feed/</id>""".format(
        name="thrakt",
        link_url="https://" +
        os.environ["SERVICE_DOMAIN"] +
        "/bookmark_new_illust.php",
        updated=datetime.strptime(
            first_item["reuploaded_time"] + "+0900", '%Y-%m-%d %H:%M:%S%z').isoformat(),
        host=os.environ["HOST"]
    )
    for e in json:
        xml += """
<entry>
<title>{title}</title>
<link href="{link}"/>
<id>{link}</id>
<summary type="html">
<div>{caption}</div>
<div><img src="{img_src}" /></div>
</summary>
<updated>{updated}</updated>
<author>
<name>{name}</name>
</author>
</entry>""".format(
            title=xmltext(e["title"]) or "no title",
            link="https://"+os.environ["SERVICE_DOMAIN"]+"/member_illust.php?mode=medium&amp;illust_id=" +
            str(e["id"]),
            caption=xmltext(e["caption"]) or "",
            img_src=e["image_urls"]["px_480mw"] or "",
            updated=datetime.strptime(
                e["reuploaded_time"] + "+0900", '%Y-%m-%d %H:%M:%S%z').isoformat(),
            name=xmltext(e["user"]["name"]) or "no name"
        )

    xml += "</feed>"

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/xml"
        },
        "body": xml
    }


def xmltext(s):
    if not s:
        return None
    r = ""
    for a in str(s):
        r += "&#"+str(ord(a))+";"
    return r


def get_access_token():
    logger.info("getting stored access token")
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table("PFavFeedInstants")
    queryData = table.query(
        KeyConditionExpression=Key('name').eq("accessToken"),
        Limit=1
    )

    if(queryData["Items"]):
        return queryData["Items"][0]["value"]
    else:
        return reflesh_access_token()


def reflesh_access_token():
    logger.info("reflesh access token")
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table("PFavFeedInstants")

    localtime = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+00:00')

    json = requests.post(
        os.environ["ACCESS_TOKEN_URL"],
        {
            "username": os.environ["USERNAME"],
            "password": os.environ["PASSWORD"],
            "client_id": os.environ["CLIENT_ID"],
            "client_secret": os.environ["CLIENT_SECRET"],
            "grant_type": "password"
        },
        headers={
            'User-Agent': os.environ['USER_AGENT'],
            'X-Client-Time': localtime,
            'X-Client-Hash': hashlib.md5((localtime + os.environ['HASH_SECRET']).encode('utf-8')).hexdigest(),
        },
        timeout=2
    ).json()

    accessToken = json["response"]["access_token"]

    table.put_item(
        Item={
            'name': "accessToken",
            'value': accessToken
        }
    )

    return accessToken


def get_latest():
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table("PFavFeedInstants")
    queryData = table.query(
        KeyConditionExpression=Key('name').eq("latest"),
        Limit=1
    )

    if(queryData["Items"]):
        return queryData["Items"][0]["value"]
    else:
        return ""


def update_latest(latest):
    logger.info("update lateest : "+str(latest))
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table("PFavFeedInstants")
    table.put_item(
        Item={
            'name': "latest",
            'value': latest
        }
    )
