import logging
from typing import Annotated

from bson.json_util import dumps, loads
from pydantic import BaseModel, ConfigDict, Field

from src.persistence.replay_store import ReplayStore, get_replay_store
from src.replays.types import Replay
from src.runtime.settings import load_current_settings

from ..utils import force_valid_json_string
from .base import AIFunction

from log import DEFAULT_LOGGER_NAME
log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")

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


QUERY_REPLAY_DB_DESCRIPTION = """Query the replay database and return JSON representation of all matching replays.

The replay DB is a MongoDB database. Query this according to your instructions. Here are a few examples of how to translate questions to query filters:

Q: Get replays of player Driftoss on the map Hecate LE
F: {{"players.name": "Driftoss", "map_name": "Hecate LE"}}
Q: Get replays against my Protoss opponents
F: {"players": {$elemMatch: {"play_race": "Protoss", "name": {$ne: "<student-name>"}}}}
Q: Get replays against my Protoss opponents who build an oracle
F: {"players.build_order": {$elemMatch: {"name": "Oracle"}} ,"players": {$elemMatch: {"play_race": "Protoss", "name": {$ne: "<student-name>"}}}}
"""


class QueryReplayDBArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filter: str = Field(
        description='A MongoDB query document to run against the replay collection. Example query to get replays for a player called Driftoss: {"players.name": "Driftoss"}'
    )
    projection: str | None = Field(
        ...,
        description='A MongoDB projection document to specifiy which fields of the document to return. Example projection to get only the map name for returned replays: {"map_name": 1}. Set null to use the local default projection.',
    )
    sort: str | None = Field(
        ...,
        description='A MongoDB sort document to specify how to sort the returned documents. Example to sort by game length: {"game_length": -1}. Set null to use the local default sort.',
    )
    limit: int | None = Field(
        ...,
        description="An integer to specify the maximum number of documents to return. Set null to use the local default of 10.",
    )
    limit_time: int | None = Field(
        ...,
        description="An integer to specify the maximum number of seconds to include results from. When limit_time is given, arrays in the result set are filtered to only include elements up to that time. Set null to use the local default of 600.",
    )


def _query_replay_db(
    filter: Annotated[
        str,
        'A MongoDB query document to run against the replay collection. Example query to get replays for a player called Driftoss: {"players.name": "Driftoss"}',
    ],
    projection: Annotated[
        str,
        'A MongoDB projection document to specifiy which fields of the document to return. Example projection to get only the map name for returned replays: {"map_name": 1}. This is optional and defaults to returning all fields.',
    ] = dumps(load_current_settings().default_projection),
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
    ] = 600,
    replay_store: ReplayStore | None = None,
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
    settings = load_current_settings()
    if filter is None or filter == "{{}}":
        filter = f'{{"player.name": "{settings.student.name}"}}'
    filter = force_valid_json_string(filter)
    projection = force_valid_json_string(projection)
    sort = force_valid_json_string(sort)

    # AI doesn't know yet that .$. is invalid as of Mongo 4.4
    projection = projection.replace(".$.", ".")

    try:
        replay_store = replay_store or get_replay_store()
        cursor = replay_store.replays.find(
            filter=loads(str(filter)),
            sort=loads(str(sort)),
            limit=limit,
        )
        results = list(cursor)
        result_replays: list[Replay] = []
        for result in results:
            try:
                r = Replay(**result)
                result_replays.append(r)
            except Exception as e:
                log.debug(f"Failed to parse replay: {e}")
                pass
        return [
            result_replay.projection(limit=limit_time, projection=loads(projection))
            for result_replay in result_replays
        ]
    except Exception as e:
        log.error(e)
        return []


def build_query_replay_db_function(replay_store: ReplayStore):
    return AIFunction(
        fn=lambda **kwargs: _query_replay_db(replay_store=replay_store, **kwargs),
        args_model=QueryReplayDBArgs,
        name="QueryReplayDB",
        description=QUERY_REPLAY_DB_DESCRIPTION,
    )


QueryReplayDB = AIFunction(
    fn=_query_replay_db,
    args_model=QueryReplayDBArgs,
    name="QueryReplayDB",
    description=QUERY_REPLAY_DB_DESCRIPTION,
)
