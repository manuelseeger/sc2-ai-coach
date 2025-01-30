from pydantic_core import ValidationError
from pymongo.collection import Collection
from pyodmongo import DbEngine, ResponsePaginate
from pyodmongo.models.responses import DbResponse
from pyodmongo.queries import eq, sort

from config import config

from .types import Metadata, PlayerInfo, Replay, Session

SC2Model = Replay | Metadata | Session | PlayerInfo


class ReplayDB:
    def __init__(self):
        self.db = DbEngine(mongo_uri=str(config.mongo_dsn), db_name=config.db_name)
        self.replays: Collection = self.db._db["replays"]
        self.meta: Collection = self.db._db["replays.meta"]

    def upsert(self, model: SC2Model) -> DbResponse:
        ModelClass = model.__class__
        try:
            return self.db.save(model, query=eq(ModelClass.id, model.id))
        except ValidationError as e:
            # On INSERT, pyodm forces the returned ID into mongo ObjectId and throws since we use a custom ID field
            # Return DbResponse without validation instead
            return DbResponse.model_construct(
                **{
                    "acknowledged": True,
                    "upserted_ids": {0: model.id},
                    "matched_count": 0,
                    "modified_count": 0,
                }
            )

    def get_most_recent(self) -> Replay:
        most_recent = self.db.find_one(
            Model=Replay,
            raw_query={"players.name": config.student.name},
            sort=sort((Replay.unix_timestamp, -1)),
        )
        if most_recent is None:
            raise ValueError(f"No replays found for {config.student.name}")

        return most_recent

    def find(self, model: SC2Model) -> SC2Model:
        ModelClass = model.__class__
        q = eq(ModelClass.id, model.id)
        return self.db.find_one(Model=ModelClass, query=q)

    def find_many_dict(self, model, raw_query: dict):
        current_page = 1
        while True:
            response: ResponsePaginate = self.db.find_many(
                Model=model,
                paginate=True,
                current_page=current_page,
                docs_per_page=100,
                raw_query=raw_query,
                as_dict=True,
            )
            for doc in response.docs:
                yield doc

            if current_page >= response.page_quantity:
                break
            current_page += 1


replaydb = ReplayDB()
