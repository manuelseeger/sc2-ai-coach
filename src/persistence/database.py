from __future__ import annotations

from datetime import tzinfo
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict
from pyodmongo import DbEngine

from src.runtime.settings import get_config

if TYPE_CHECKING:
    from src.runtime.settings import Config


class MongoDatabaseConfig(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    mongo_uri: str
    db_name: str
    tz_info: tzinfo | None = None

    @classmethod
    def from_config(cls, app_config: Config) -> MongoDatabaseConfig:
        return cls(mongo_uri=str(app_config.mongo_dsn), db_name=app_config.db_name)


class MongoDatabase:
    def __init__(self, config: MongoDatabaseConfig):
        self.config = config
        self._engine: DbEngine | None = None

    @property
    def engine(self) -> DbEngine:
        if self._engine is None:
            self._engine = DbEngine(
                mongo_uri=self.config.mongo_uri,
                db_name=self.config.db_name,
            )
        return self._engine

    @property
    def raw(self) -> Any:
        return self.engine._db


_database: MongoDatabase | None = None


def get_database(app_config: Config | None = None) -> MongoDatabase:
    global _database

    if app_config is None:
        if _database is None:
            _database = MongoDatabase(
                MongoDatabaseConfig.from_config(get_config())
            )
        return _database

    database = MongoDatabase(MongoDatabaseConfig.from_config(app_config))
    if _database is None or _database.config != database.config:
        _database = database
    return _database


def set_database(database: MongoDatabase) -> MongoDatabase:
    global _database
    _database = database
    return database


def reset_database() -> None:
    global _database
    _database = None
