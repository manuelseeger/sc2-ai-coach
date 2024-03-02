from pyodmongo import DbEngine
import os
from config import config
from .types import Replay
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
        self.engine = engine
        self.replays = self.engine._db["replays"]
        self.meta = self.engine._db["replays.meta"]

    def upsert(self, replay: Replay):
        try:
            return self.engine.save(replay, query=eq(Replay.id, replay.id))
        except ValidationError as e:
            return None

    def get_most_recent(self) -> Replay:
        most_recent = engine._db.replays.find().sort("unix_timestamp", -1).limit(1)[0]
        return Replay(**most_recent)

    def find(self, Model):
        return self.engine.find(Model)


replaydb = ReplayDB()
