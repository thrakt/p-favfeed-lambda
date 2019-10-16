# Get P favorite feed

This application get P favorite creators items to ATOM feeds.

`/` get feed.

### requires

* Dynamo DB tables.
`PFavFeedInstants` with string patition key `name`

#### deploy

1. set up apex http://apex.run/
2. execut init to create iam role. input project name you like.
```
apex init
```
3. remove created `hello` project.
4. execute apex with variables:
```
apex deploy -s USERNAME=... -s PASSWORD=...
```
* USERNAME
* PASSWORD
* CLIENT_ID
* CLIENT_SECRET
* HASH_SECRET
* USER_AGENT
* SERVICE_DOMAIN
* JSON_API_URL
* ACCESS_TOKEN_URL
* HOST
5. set CloudWatch and API Gateway manually.
