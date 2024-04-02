# Local mongo DB

This expects a production DB with replay data populated and credentials stored in 

../.env.production

Set credentials for local mongodb in 

./.env

```env
MONGO_INITDB_ROOT_USERNAME="root"
MONGO_INITDB_ROOT_PASSWORD="xxx"
DBOWNER_USERNAME="sc2"
DBOWNER_PASSWORD="yyy"
```

Run export.nu (for nushell) or a similar script to export from production. Start up and populate local DB with dockercompose up.

Note: Name of the DB in mongo is hardcoded to "SC2".