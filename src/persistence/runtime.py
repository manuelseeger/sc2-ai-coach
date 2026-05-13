from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.persistence.conversation_store import ConversationStore
from src.persistence.database import MongoDatabase, MongoDatabaseConfig
from src.persistence.replay_store import ReplayStore
from src.persistence.session_store import SessionStore

if TYPE_CHECKING:
    from src.runtime.settings import Config


@dataclass(frozen=True)
class PersistenceServices:
    database: MongoDatabase
    replay_store: ReplayStore
    conversation_store: ConversationStore
    session_store: SessionStore


def build_persistence_services(settings: "Config") -> PersistenceServices:
    database = MongoDatabase(MongoDatabaseConfig.from_config(settings))
    return PersistenceServices(
        database=database,
        replay_store=ReplayStore(database),
        conversation_store=ConversationStore(database),
        session_store=SessionStore(database),
    )