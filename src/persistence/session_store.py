from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from pydantic import Field
from pyodmongo import DbModel, Id
from pyodmongo.queries import eq

from config import AIBackend
from src.persistence.database import MongoDatabase, get_database

if TYPE_CHECKING:
    from src.persistence.conversation_store import AIResponseRecord


class Session(DbModel):
    conversations: list[Id | str] = Field(default_factory=list)
    current_conversation: Id | str | None = None
    twitch_conversation: Id | str | None = None
    ai_backend: AIBackend
    session_date: datetime
    completion_pricing: float
    prompt_pricing: float
    cached_prompt_pricing: float = 0
    total_input_tokens: int = 0
    total_cached_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0

    _collection: ClassVar = "sessions"

    def add_response_record(self, record: AIResponseRecord) -> None:
        self.total_input_tokens += record.input_tokens
        self.total_cached_tokens += record.cached_tokens
        self.total_output_tokens += record.output_tokens
        self.total_tokens += record.total_tokens
        self.total_cost += record.total_cost


class SessionStore:
    def __init__(self, database: MongoDatabase | None = None):
        self._database = database

    @property
    def database(self) -> MongoDatabase:
        if self._database is None:
            self._database = get_database()
        return self._database

    @property
    def db(self):
        return self.database.engine

    def create(
        self, session_date: datetime, ai_backend: AIBackend, **fields
    ) -> Session:
        return self.save(
            Session(session_date=session_date, ai_backend=ai_backend, **fields)
        )

    def save(self, session: Session) -> Session:
        self.db.save(session)
        return session

    def get(self, session_or_id: Session | Id | str) -> Session | None:
        session_id = self._id(session_or_id)
        return self.db.find_one(
            Model=Session,
            query=eq(Session.id, session_id),  # type: ignore[arg-type]
        )

    def set_current_conversation(
        self, session: Session | Id | str, conversation_id: str | None
    ) -> Session:
        reloaded = self._require_session(session)
        reloaded.current_conversation = conversation_id
        if (
            conversation_id is not None
            and conversation_id not in reloaded.conversations
        ):
            reloaded.conversations.append(conversation_id)
        return self.save(reloaded)

    def set_twitch_conversation(
        self, session: Session | Id | str, conversation_id: str | None
    ) -> Session:
        reloaded = self._require_session(session)
        reloaded.twitch_conversation = conversation_id
        if (
            conversation_id is not None
            and conversation_id not in reloaded.conversations
        ):
            reloaded.conversations.append(conversation_id)
        return self.save(reloaded)

    def add_response_record(
        self, session: Session | Id | str, record: AIResponseRecord
    ) -> Session:
        reloaded = self._require_session(session)
        reloaded.add_response_record(record)
        return self.save(reloaded)

    def _require_session(self, session: Session | Id | str) -> Session:
        reloaded = self.get(session)
        if reloaded is None:
            raise ValueError(f"Session {self._id(session)} not found")
        return reloaded

    def _id(self, value: Session | Id | str) -> Id:
        if isinstance(value, str):
            return Id(value)
        model_id = getattr(value, "id", value)
        if model_id is None:
            raise ValueError("Session must be saved before use")
        return Id(model_id)
