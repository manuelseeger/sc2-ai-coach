from pyodmongo import DbEngine
import os
from config import config
from .types import Replay, Metadata
from pyodmongo.queries import eq
from pydantic_core import ValidationError

MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASS = os.environ.get("MONGO_PASS")
MONGO_HOST = os.environ.get("MONGO_HOST")

mongo_uri = (
    f"mongodb+srv://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}/?retryWrites=true&w=majority"
)

# Initialize the database engine
engine = DbEngine(mongo_uri=mongo_uri, db_name=config.db_name)


class ReplayDB:
    def __init__(self):
        self.db = engine
        self.replays = self.db._db["replays"]
        self.meta = self.db._db["replays.meta"]

    def upsert(self, model: Replay | Metadata):
        try:
            if isinstance(model, Replay):
                return self.db.save(model, query=eq(Replay.id, model.id))
            elif isinstance(model, Metadata):
                return self.db.save(model, query=eq(Metadata.id, model.id))
        except ValidationError as e:
            return None

    def get_most_recent(self) -> Replay:
        most_recent = engine._db.replays.find().sort("unix_timestamp", -1).limit(1)[0]
        return Replay(**most_recent)

    def find(self, Model):
        return self.db.find(Model)


replaydb = ReplayDB()
