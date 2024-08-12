import logging
from typing import Annotated

from bson.json_util import dumps, loads

from config import config
from replays.db import replaydb
from replays.types import Replay

from ..utils import force_valid_json_string
from .base import AIFunction

log = logging.getLogger(f"{config.name}.{__name__}")

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
) -> list:
    """Query the replay database and return JSON representation of all matching replays.

    The replay DB is a MongoDB database. Query this according to your instructions. Here are a few examples of how to translate questions to query filters, assuming the student talking to you is called "Johnny":

    Q: Get replays of player Driftoss on the map Hecate LE
    F: {"players.name": "Driftoss", "map_name": "Hecate LE"}
    Q: Get replays against my Protoss opponents
    F: {"players": {$elemMatch: {"play_race": "Protoss", "name": {$ne: "Johnny"}}}}
    Q: Get replays against my Protoss opponents who build an oracle
    F: {"players.build_order": {$elemMatch: {"name": "Oracle"}} ,"players": {$elemMatch: {"play_race": "Protoss", "name": {$ne: "Johnny"}}}}
    """
    # Force the arguments to be valid JSON
    if filter is None or filter == "{{}}":
        filter = f'{{"player.name": "{config.student.name}"}}'
    filter = force_valid_json_string(filter)
    projection = force_valid_json_string(projection)
    sort = force_valid_json_string(sort)

    # AI doesn't know yet that .$. is invalid as of Mongo 4.4
    projection = projection.replace(".$.", ".")

    try:
        cursor = replaydb.replays.find(
            filter=loads(str(filter)),
            sort=loads(str(sort)),
            limit=limit,
        )
        results = list(cursor)
        result_replays = [Replay(**result) for result in results]
    except Exception as e:
        log.error(e)
        return []

    return [
        result_replay.projection(limit=limit_time, projection=loads(projection))
        for result_replay in result_replays
    ]


QueryReplayDB.__doc__ = f"""Query the replay database and return JSON representation of all matching replays.

    The replay DB is a MongoDB database. Query this according to your instructions. Here are a few examples of how to translate questions to query filters:

    Q: Get replays of player Driftoss on the map Hecate LE
    F: {{"players.name": "Driftoss", "map_name": "Hecate LE"}}
    Q: Get replays against my Protoss opponents
    F: {{"players": {{$elemMatch: {{"play_race": "Protoss", "name": {{$ne: "{config.student.name}"}}}}}}}}
    Q: Get replays against my Protoss opponents who build an oracle
    F: {{"players.build_order": {{$elemMatch: {{"name": "Oracle"}}}} ,"players": {{$elemMatch: {{"play_race": "Protoss", "name": {{$ne: "{config.student.name}"}}}}}}}}
    """
