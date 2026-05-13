from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, cast

from pydantic import Field, field_validator
from pymongo import ASCENDING, IndexModel
from pyodmongo import DbModel, Id
from pyodmongo.queries import eq, sort

from src.persistence.database import MongoDatabase, get_database
from src.replays.types import (
    AIContentPart,
    AIConversationItemType,
    AIConversationStatus,
    AIConversationTrigger,
    AIMessageRole,
)
from src.runtime.settings import load_current_settings

if TYPE_CHECKING:
    from src.persistence.session_store import Session

ModelT = TypeVar("ModelT")


def _data(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return {key: _value(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        return _data(value.model_dump(mode="python"))
    if hasattr(value, "__dict__"):
        return {key: _value(item) for key, item in vars(value).items()}
    return {key: _value(item) for key, item in dict(value).items()}


def _value(value: Any) -> Any:
    if isinstance(value, dict):
        return _data(value)
    if isinstance(value, (list, tuple)):
        return [_value(item) for item in value]
    if hasattr(value, "model_dump") or hasattr(value, "__dict__"):
        return _data(value)
    return value


class AIConversation(DbModel):
    session: Id | str | None = None
    trigger: AIConversationTrigger
    status: AIConversationStatus = AIConversationStatus.active
    closed_at: datetime | None = None

    developer_instructions: str | None = None
    handler_context: str | None = None
    prompt_template: str | None = None
    prompt_version: str | None = None

    replay_id: str | None = None
    map_name: str | None = None
    opponent: str | None = None
    twitch_user: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    item_count: int = 0
    last_item_at: datetime | None = None
    last_response_id: str | None = None
    total_input_tokens: int = 0
    total_cached_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0

    _collection: ClassVar = "ai_conversations"
    _indexes: ClassVar = [
        IndexModel(
            [("session", ASCENDING), ("trigger", ASCENDING), ("created_at", ASCENDING)]
        )
    ]

    @field_validator("metadata", mode="before")
    @classmethod
    def _default_metadata(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        if value is None:
            return {}
        return value

    def close(self) -> None:
        self.status = AIConversationStatus.closed
        self.closed_at = datetime.now()

    def add_item(self, item: AIConversationItem) -> None:
        self.last_item_at = item.created_at
        self.item_count += 1

    def add_response_record(self, record: AIResponseRecord) -> None:
        self.last_response_id = record.response_id
        self.total_input_tokens += record.input_tokens
        self.total_cached_tokens += record.cached_tokens
        self.total_output_tokens += record.output_tokens
        self.total_tokens += record.total_tokens
        self.total_cost += record.total_cost


class AIConversationItem(DbModel):
    conversation: Id | str
    session: Id | str | None = None
    type: AIConversationItemType
    order: int

    role: AIMessageRole | None = None
    content: list[AIContentPart] = Field(default_factory=list)

    call_id: str | None = None
    name: str | None = None
    arguments: dict[str, Any] | None = None
    output: str | None = None

    response_id: str | None = None
    response_model: str | None = None
    status: str | None = None
    raw_item: dict[str, Any] | None = None

    source: str | None = None
    included_in_context: bool = True
    metadata: dict[str, Any] | None = Field(default_factory=dict)

    _collection: ClassVar = "ai_conversation_items"
    _indexes: ClassVar = [
        IndexModel(
            [("conversation", ASCENDING), ("order", ASCENDING)],
            unique=True,
            partialFilterExpression={"conversation": {"$exists": True}},
        ),
        IndexModel([("conversation", ASCENDING), ("created_at", ASCENDING)]),
    ]


class AIResponseRecord(DbModel):
    conversation: Id | str
    session: Id | str | None = None
    response_id: str | None = None
    model: str | None = None
    status: str | None = None
    streamed: bool = False

    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_cost: float = 0
    cached_input_cost: float = 0
    output_cost: float = 0
    total_cost: float = 0

    raw_usage: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    _collection: ClassVar = "ai_responses"
    _indexes: ClassVar = [
        IndexModel([("conversation", ASCENDING), ("created_at", ASCENDING)]),
        IndexModel([("response_id", ASCENDING)], unique=True, sparse=True),
    ]

    @field_validator("metadata", mode="before")
    @classmethod
    def _default_metadata(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        if value is None:
            return {}
        return value

    @classmethod
    def from_response(
        cls,
        conversation: AIConversation,
        response: Any,
        streamed: bool = False,
    ) -> AIResponseRecord:
        response_data = _data(response)
        usage = _data(response_data.get("usage"))
        input_details = _data(usage.get("input_tokens_details"))
        response_id = response_data.get("id") or response_data.get("response_id")
        model = response_data.get("model")

        input_tokens = int(usage.get("input_tokens") or 0)
        cached_tokens = int(input_details.get("cached_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)

        pricing = load_current_settings().get_model_pricing(model)
        input_cost = max(0, input_tokens - cached_tokens) * pricing.prompt
        cached_input_cost = cached_tokens * pricing.cached_prompt
        output_cost = output_tokens * pricing.completion

        return cls(
            conversation=Id(conversation.id),
            session=conversation.session,
            response_id=response_id,
            model=model,
            status=response_data.get("status"),
            streamed=streamed,
            input_tokens=input_tokens,
            cached_tokens=cached_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_cost=input_cost,
            cached_input_cost=cached_input_cost,
            output_cost=output_cost,
            total_cost=input_cost + cached_input_cost + output_cost,
            raw_usage=usage or None,
        )


class ConversationStore:
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

    def create_conversation(
        self,
        trigger: AIConversationTrigger | str,
        session: Session | None = None,
        initial_message: str | tuple[AIMessageRole | str, str] | None = None,
        handler_context: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AIConversation:
        conversation = self.save(
            AIConversation(
                trigger=AIConversationTrigger(trigger),
                session=self._id(session) if session is not None else None,
                handler_context=handler_context,
                metadata=metadata or {},
            )
        )

        if initial_message is not None:
            role, text = self._message_parts(initial_message)
            self.append_message(conversation, role=role, text=text)
            return self.get_conversation(conversation) or conversation

        return conversation

    def get_conversation(
        self, conversation: AIConversation | Id | str
    ) -> AIConversation | None:
        return self.db.find_one(
            Model=AIConversation,
            query=eq(AIConversation.id, self._id(conversation)),  # type: ignore[arg-type]
        )

    def append_message(
        self,
        conversation: AIConversation | Id | str,
        role: AIMessageRole | str,
        text: str,
        source: str | None = None,
    ) -> AIConversationItem:
        return self._append_item(
            conversation,
            type=AIConversationItemType.message,
            role=AIMessageRole(role),
            content=[AIContentPart(text=text)],
            source=source,
        )

    def append_function_call(
        self,
        conversation: AIConversation | Id | str,
        call_id: str,
        name: str,
        arguments: dict[str, Any],
        response_id: str | None = None,
    ) -> AIConversationItem:
        return self._append_item(
            conversation,
            type=AIConversationItemType.function_call,
            call_id=call_id,
            name=name,
            arguments=arguments,
            response_id=response_id,
        )

    def append_function_call_output(
        self,
        conversation: AIConversation | Id | str,
        call_id: str,
        output: str,
    ) -> AIConversationItem:
        return self._append_item(
            conversation,
            type=AIConversationItemType.function_call_output,
            call_id=call_id,
            output=output,
        )

    def append_assistant_response(
        self,
        conversation: AIConversation | Id | str,
        text: str,
        response_id: str | None,
        model: str | None,
    ) -> AIConversationItem:
        return self._append_item(
            conversation,
            type=AIConversationItemType.message,
            role=AIMessageRole.assistant,
            content=[AIContentPart(text=text)],
            response_id=response_id,
            response_model=model,
        )

    def list_items(
        self, conversation: AIConversation | Id | str, included_only: bool = True
    ) -> list[AIConversationItem]:
        conversation_id = self._id(conversation)
        query = eq(AIConversationItem.conversation, conversation_id)  # type: ignore[arg-type]
        if included_only:
            query = query & eq(AIConversationItem.included_in_context, True)  # type: ignore[arg-type]

        return cast(
            list[AIConversationItem],
            self.db.find_many(
                Model=AIConversationItem,
                query=query,
                sort=sort((AIConversationItem.order, 1)),  # type: ignore[arg-type]
            ),
        )

    def close_conversation(self, conversation: AIConversation | Id | str) -> None:
        conversation = self._conversation(conversation)
        conversation.close()
        self.save(conversation)

    def record_response(
        self,
        conversation: AIConversation | Id | str,
        response: Any,
        streamed: bool = False,
    ) -> AIResponseRecord:
        conversation = self._conversation(conversation)
        record = AIResponseRecord.from_response(conversation, response, streamed)

        if record.response_id is not None:
            existing = self.db.find_one(
                Model=AIResponseRecord,
                query=AIResponseRecord.response_id == record.response_id,  # type: ignore
            )
            if existing is not None:
                return existing

        self.save(record)
        conversation.add_response_record(record)
        self.save(conversation)

        session = self._session(conversation.session)
        if session is not None:
            session.add_response_record(record)
            self.save(session)

        return record

    def delete_conversations(
        self, conversations: list[AIConversation | Id | str]
    ) -> None:
        for conversation in conversations:
            conversation_id = self._id(conversation)
            item_query = eq(AIConversationItem.conversation, conversation_id)  # type: ignore[arg-type]
            conversation_query = eq(AIConversation.id, conversation_id)  # type: ignore[arg-type]
            self.db.delete(AIConversationItem, query=item_query)
            self.db.delete(AIConversation, query=conversation_query)

    def delete_response_records(self, response_records: list[AIResponseRecord]) -> None:
        for response_record in response_records:
            response_id = self._id(response_record)
            response_query = eq(AIResponseRecord.id, response_id)  # type: ignore[arg-type]
            self.db.delete(AIResponseRecord, query=response_query)

    def save(self, model: ModelT) -> ModelT:
        self.db.save(model)  # type: ignore
        return model

    def _next_order(self, conversation: AIConversation) -> int:
        latest = self.db.find_one(
            Model=AIConversationItem,
            query=eq(AIConversationItem.conversation, self._id(conversation)),  # type: ignore[arg-type]
            sort=sort((AIConversationItem.order, -1)),  # type: ignore[arg-type]
        )
        if latest is None:
            return 0
        return int(latest.order) + 1

    def _append_item(
        self,
        conversation: AIConversation | Id | str,
        **fields: Any,
    ) -> AIConversationItem:
        conversation_id = self._id(conversation)
        conversation = self._conversation(conversation)
        item = self.save(
            AIConversationItem(
                conversation=conversation_id,
                session=conversation.session,
                order=self._next_order(conversation),
                **fields,
            )
        )
        conversation.add_item(item)
        self.save(conversation)
        return item

    def _conversation(self, conversation: AIConversation | Id | str) -> AIConversation:
        found = self.get_conversation(conversation)
        if found is None:
            raise ValueError(f"Conversation {self._id(conversation)} not found")
        return found

    def _session(self, session: Id | str | None):
        if session is None:
            return None
        from src.persistence.session_store import Session

        return self.db.find_one(
            Model=Session,
            query=eq(Session.id, self._id(session)),  # type: ignore[arg-type]
        )

    def _id(self, value: Any) -> Id:
        if isinstance(value, str):
            return cast(Id, value)
        model_id = getattr(value, "id", value)
        if model_id is None:
            raise ValueError("Object must be saved before use")
        return cast(Id, model_id)

    def _message_parts(
        self, message: str | tuple[AIMessageRole | str, str]
    ) -> tuple[AIMessageRole, str]:
        if isinstance(message, tuple):
            return AIMessageRole(message[0]), message[1]
        return AIMessageRole.user, message


_conversation_store: ConversationStore | None = None


def get_conversation_store(
    database: MongoDatabase | None = None,
) -> ConversationStore:
    global _conversation_store

    if database is not None:
        return ConversationStore(database)
    if _conversation_store is None:
        _conversation_store = ConversationStore()
    return _conversation_store


def reset_conversation_store() -> None:
    global _conversation_store
    _conversation_store = None
