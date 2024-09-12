# Local mongo DB

Set credentials for local mongodb in 

./.env

```env
MONGO_INITDB_ROOT_USERNAME="root"
MONGO_INITDB_ROOT_PASSWORD="xxx"
DBOWNER_USERNAME="sc2"
DBOWNER_PASSWORD="yyy"
DB_NAME="MyReplays"
```

Startup local DB with 

```sh
dockercompose up
```
This will set up a locally running MongoDB with database $DB_NAME and the credentials from the .env file. Populate it by importing from an existing DB or import replays with [../repcli.py](../repcli.py).

## Seed with export from production DB

(Optional) On startup the seed service will look for *.json files in /mongo-seed and import them into the newly created DB into the collection `replays`. If no files can be found nothing is imported.

To export from production DB put credentials in 

../.env.production

Run export.nu (for nushell) or a similar script to export from production. Start up and populate local DB with dockercompose up.