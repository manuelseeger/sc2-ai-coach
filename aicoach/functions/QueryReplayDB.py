from .base import AIFunction
from typing import Annotated
import os
import pymongo
from pymongo.server_api import ServerApi
from bson.json_util import loads, dumps
import ast
import json
import logging
from config import config
from replays import time2secs

log = logging.getLogger(config.name)

MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASS = os.environ.get("MONGO_PASS")
MONGO_HOST = os.environ.get("MONGO_HOST")

client = pymongo.MongoClient(
    f"mongodb+srv://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}/?retryWrites=true&w=majority",
    server_api=ServerApi("1"),
)
database = client.SC2
db = database.replays

example = """
{
  "_id": "ebf5056314ee19f959925afe9312c0a8803e11d52709dc144a9328b6f108db9c",
  "game_length": 1289,
  "map_name": "Hecate LE",
  "players": [
    {
      "avg_apm": 171.35627081021087,
      "build_order": [
        {
          "time": "0:00",
          "name": "SCV",
          "supply": 12,
          "is_chronoboosted": false
        },
        {
          "time": "0:12",
          "name": "SCV",
          "supply": 13,
          "is_chronoboosted": false
        },
      ],
      "highest_league": 5,
      "name": "BabouLeFou",
      "messages": [],
      "pick_race": "Terran",
      "pid": 1,
      "play_race": "Terran",
      "result": "Loss",
      "scaled_rating": 4005,
      "stats": {
        "worker_split": 0,
        "worker_micro": 0
      },
      "toon_handle": "2-S2-1-1849098",
    },
    {
      "avg_apm": 317.7573407202216,
      "build_order": [
        {
          "time": "0:00",
          "name": "Drone",
          "supply": 12,
          "is_chronoboosted": false
        },
      ],
      "highest_league": 5,
      "name": "zatic",
      "messages": [
        {
          "pid": 1,
          "second": 0,
          "text": "glhf",
        }
      ],
      "pick_race": "Zerg",
      "pid": 2,
      "play_race": "Zerg",
      "result": "Win",
      "scaled_rating": 3992,
      "stats": {
        "worker_split": 1,
        "worker_micro": 0
      },
      "toon_handle": "2-S2-1-691545",
      }
  ],
  "real_length": 1289,
  "stats": {
    "loserDoesGG": false
  },
  "unix_timestamp": 1703779713,
}
"""

default_projection = {
    "_id": 1,
    "date": 1,
    "game_length": 1,
    "map_name": 1,
    "players.avg_apm": 1,
    "players.highest_league": 1,
    "players.name": 1,
    "players.messages": 1,
    "players.pick_race": 1,
    "players.pid": 1,
    "players.play_race": 1,
    "players.result": 1,
    "players.scaled_rating": 1,
    "players.stats": 1,
    "players.toon_handle": 1,
    "players.build_order.time": 1,
    "players.build_order.name": 1,
    "players.build_order.supply": 1,
    "players.build_order.is_chronoboosted": 1,
    "real_length": 1,
    "stats": 1,
    "unix_timestamp": 1,
}


def duration_to_seconds(duration_str):
    minutes, seconds = duration_str.split(":")
    return int(minutes) * 60 + int(seconds)


@AIFunction
def QueryReplayDB(
    filter: Annotated[
        str,
        'A MongoDB query document to run against the replay collection. Example query to get replays for a player called Driftoss: {"players.name": "Driftoss"}',
    ],
    projection: Annotated[
        str,
        'A MongoDB projection document to specifiy which fields of the document to return. Example projection to get only the map name for returned replays: {"map_name": 1}. This is optional and defaults to returning all fields.',
    ] = dumps(default_projection),
    sort: Annotated[
        str,
        'A MongoDB sort document to specify how to sort the returned documents. Example to sort by game length: {"game_length": -1}. This is optional and defaults to sorting by unix_timestamp, descending.',
    ] = '{"unix_timestamp": -1}',
    limit: Annotated[
        int,
        "An integer to specify the maximum number of documents to return. This is optional and defaults to 10.",
    ] = 10,
    limit_time: Annotated[
        int,
        "An integer to specify the maximum number of seconds to include results from. When limit_time is given, arrays in the result set are filtered to only include elements up to that time. This is optional.",
    ] = None,
) -> str:
    """Query the replay database and return JSON representation of all matching replays.

    The replay DB is a MongoDB database. The collection you will query contains replays in the format given in your instructions.

    Query and projection documents need to be compatible with MongoDB version 4.4 and up.
    """
    # Force the arguments to be valid JSON
    if filter is None or filter == "{}":
        filter = f'{{player.name: "{config.student.name}"}}'
    filter = ast.literal_eval(json.dumps(filter))
    projection = ast.literal_eval(json.dumps(projection))
    sort = ast.literal_eval(json.dumps(sort))

    # AI doesn't know yet that .$. is invalid as of Mongo 4.4
    projection = projection.replace(".$.", ".")

    results = []
    try:
        cursor = db.find(
            filter=loads(str(filter)),
            projection=loads(str(projection)),
            sort=loads(str(sort)),
            limit=limit,
        )
        results = list(cursor)
        # Filter build orders to only include events up to limit_time
        # The aggregation needed to do this in DB is too complex for the AI assistant
        if limit_time:
            for result in results:
                for player in result["players"]:
                    player["build_order"] = [
                        bo
                        for bo in player["build_order"]
                        if duration_to_seconds(bo["time"]) <= limit_time
                    ]
    except Exception as e:
        log.error(e)
        return []

    return results
