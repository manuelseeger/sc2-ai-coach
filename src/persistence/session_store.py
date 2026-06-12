from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from pydantic import Field
from pyodmongo import DbModel, Id, ResponsePaginate
from pyodmongo.queries import eq, sort

from persistence.database import MongoDatabase, get_database
from runtime.settings import AIBackend

if TYPE_CHECKING:
    from persistence.conversation_store import AIResponseRecord


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

    def list(
        self,
        *,
        current_page: int = 1,
        docs_per_page: int = 50,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        ai_backend: AIBackend | None = None,
    ) -> ResponsePaginate:
        raw_query: dict[str, object] = {}
        if from_date is not None or to_date is not None:
            session_date_query: dict[str, datetime] = {}
            if from_date is not None:
                session_date_query["$gte"] = from_date
            if to_date is not None:
                session_date_query["$lte"] = to_date
            raw_query["session_date"] = session_date_query

        if ai_backend is not None:
            raw_query["ai_backend"] = ai_backend.value

        return self.db.find_many(
            Model=Session,
            paginate=True,
            current_page=current_page,
            docs_per_page=docs_per_page,
            raw_query=raw_query,
            sort=sort((Session.session_date, -1)),  # type: ignore[arg-type]
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
