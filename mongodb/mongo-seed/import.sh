#!/bin/bash
if [ -z "$(ls -A /mongo-seed/*.json 2>/dev/null)" ]; then
  echo "No json files to import"
  exit 0
fi
shopt -s extglob
# import any *json file with mongo import:
for f in /mongo-seed/*.json; do
  echo "Processing $f file..."
  mongoimport --username $DBOWNER_USERNAME --password $DBOWNER_PASSWORD --host mongodb --db SC2 --collection "${f//+(*\/|.*)}" --type json --file $f --jsonArray
done
