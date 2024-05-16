from typing import Union

from pydantic_core import ValidationError
from pymongo.collection import Collection
from pyodmongo import DbEngine, DbModel
from pyodmongo.queries import eq

from config import config

from .types import Metadata, Replay, Session

# Initialize the database engine
engine = DbEngine(mongo_uri=str(config.mongo_dsn), db_name=config.db_name)

SC2Model = Union[Replay, Metadata, Session]


class ReplayDB:
    def __init__(self):
        self.db = engine
        self.replays: Collection = self.db._db["replays"]
        self.meta: Collection = self.db._db["replays.meta"]

    def upsert(self, model: SC2Model):
        ModelClass = model.__class__
        try:
            return self.db.save(model, query=eq(ModelClass.id, model.id))
        except ValidationError as e:
            # pyodm forces the returned ID into mongo ObjectId and throws
            # since we use a custom ID field
            return None

    def get_most_recent(self) -> Replay:
        most_recents = list(
            engine._db.replays.find().sort("unix_timestamp", -1).limit(1)
        )
        if len(most_recents) == 0:
            raise ValueError("No replays found")

        if len(most_recents) > 1:
            raise ValueError("Multiple replays found")

        return Replay(**most_recents[0])

    def find(self, model: SC2Model) -> SC2Model:
        ModelClass = model.__class__
        q = eq(ModelClass.id, model.id)
        return self.db.find_one(Model=ModelClass, query=q)


replaydb = ReplayDB()
