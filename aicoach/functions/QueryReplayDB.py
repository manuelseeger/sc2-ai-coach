from .base import AIFunction
from typing import Annotated
import os
import pymongo
from pymongo.server_api import ServerApi
from bson.json_util import loads

MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASS = os.environ.get("MONGO_PASS")

client = pymongo.MongoClient(
    "mongodb+srv://{}:{}@sc2.k2kgmgk.mongodb.net/?retryWrites=true&w=majority".format(
        MONGO_USER, MONGO_PASS
    ),
    server_api=ServerApi("1"),
)
database = client.SC2
db = database.replays


@AIFunction
def QueryReplayDB(
    filter: Annotated[
        str,
        'A MongoDB query document to run against the replay collection. Example query to get replays for a player called Driftoss: {"players.name": "Driftoss"}',
    ],
    projection: Annotated[
        str,
        "A MongoDB projection document to specifiy which fields of the document to return. Example projection to get only the map name for returned replays: {'map_name': 1}",
    ],
    sort: Annotated[
        str,
        "A MongoDB sort document to specify how to sort the returned documents. Example to sort by game length: {'game_length': -1}. This is optional and defaults to sorting by unix_timestamp, descending.",
    ] = '{"unix_timestamp": -1}',
    limit: Annotated[
        int,
        "An integer to specify the maximum number of documents to return. This is optional and defaults to 10.",
    ] = 10,
) -> str:
    """Query the replay database and return JSON representation of all matching replays.

    The replay DB is a MongoDB database. The collection you will query contains replays in the format given in your instructions.
    """
    results = db.find(
        filter=loads(filter),
        projection=loads(projection),
        sort=loads(sort),
        limit=limit,
    )
    return list(results)
