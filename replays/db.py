from pyodmongo import DbEngine
from config import config
from .types import Replay, Metadata
from pyodmongo.queries import eq
from pydantic_core import ValidationError
from pymongo.collection import Collection

# Initialize the database engine
engine = DbEngine(mongo_uri=str(config.mongo_dsn), db_name=config.db_name)


class ReplayDB:
    def __init__(self):
        self.db = engine
        self.replays: Collection = self.db._db["replays"]
        self.meta: Collection = self.db._db["replays.meta"]

    def upsert(self, model: Replay | Metadata):
        try:
            if isinstance(model, Replay):
                return self.db.save(model, query=eq(Replay.id, model.id))
            elif isinstance(model, Metadata):
                return self.db.save(model, query=eq(Metadata.id, model.id))
        except ValidationError as e:
            # pyodm forces the returned ID into mongo ObjectId and throws
            # since we use a custom ID field
            return None

    def get_most_recent(self) -> Replay:
        most_recent = engine._db.replays.find().sort("unix_timestamp", -1).limit(1)[0]
        return Replay(**most_recent)

    def find(self, Model):
        return self.db.find(Model)


replaydb = ReplayDB()
