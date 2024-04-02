#! /bin/bash
mongoimport --username $DBOWNER_USERNAME --password $DBOWNER_PASSWORD --host mongodb --db SC2 --collection replays --type json --file /mongo-seed/100_most_recent.json --jsonArray