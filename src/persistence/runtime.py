from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from persistence.conversation_store import ConversationStore
from persistence.database import MongoDatabase, MongoDatabaseConfig
from persistence.replay_store import ReplayStore
from persistence.session_store import SessionStore

if TYPE_CHECKING:
    from runtime.settings import ApiSettings


@dataclass(frozen=True)
class PersistenceServices:
    database: MongoDatabase
    replay_store: ReplayStore
    conversation_store: ConversationStore
    session_store: SessionStore


def build_persistence_services(settings: "ApiSettings") -> PersistenceServices:
    database = MongoDatabase(MongoDatabaseConfig.from_config(settings))
    return PersistenceServices(
        database=database,
        replay_store=ReplayStore(database),
        conversation_store=ConversationStore(database),
        session_store=SessionStore(database),
    )
