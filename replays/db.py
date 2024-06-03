from typing import Union

from pydantic_core import ValidationError
from pymongo.collection import Collection
from pyodmongo import DbEngine, DbModel
from pyodmongo.queries import eq, sort

from config import config

from .types import Metadata, PlayerInfo, Replay, Session

# Initialize the database engine
engine = DbEngine(mongo_uri=str(config.mongo_dsn), db_name=config.db_name)

SC2Model = Union[Replay, Metadata, Session, PlayerInfo]


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
        most_recent = self.db.find_one(
            Model=Replay, sort=sort((Replay.unix_timestamp, -1))
        )
        if most_recent is None:
            raise ValueError("No replays found")

        return most_recent

    def find(self, model: SC2Model) -> SC2Model:
        ModelClass = model.__class__
        q = eq(ModelClass.id, model.id)
        return self.db.find_one(Model=ModelClass, query=q)


replaydb = ReplayDB()
