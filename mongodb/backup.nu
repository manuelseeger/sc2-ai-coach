open ../.env.production | from toml | load-env
let d = ( date now | format date "%Y-%m-%d" )
mongodump --uri $env.AICOACH_MONGO_DSN --out ( "dump/" + $d )