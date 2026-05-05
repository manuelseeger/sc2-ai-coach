from __future__ import annotations

from typing import Any, cast

from pyodmongo import Id
from pyodmongo.queries import eq, sort

from src.replaydb.db import replaydb
from src.replaydb.types import (
    AIContentPart,
    AIConversation,
    AIConversationItem,
    AIConversationItemType,
    AIConversationStatus,
    AIConversationTrigger,
    AIMessageRole,
    AIResponseRecord,
    Session,
)


def _to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return {key: _normalize_value(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        return _to_dict(value.model_dump())
    if hasattr(value, "__dict__"):
        return {key: _normalize_value(item) for key, item in vars(value).items()}
    return {key: _normalize_value(item) for key, item in dict(value).items()}


def _normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    if hasattr(value, "model_dump") or hasattr(value, "__dict__"):
        return _to_dict(value)
    return value


def _get_nested(data: dict[str, Any], *path: str, default: Any = None) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


class ConversationStore:
    def __init__(self):
        self._replaydb = replaydb

    def create_conversation(
        self,
        trigger: AIConversationTrigger | str,
        session: Session | None = None,
        initial_message: str | tuple[AIMessageRole | str, str] | None = None,
        handler_context: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AIConversation:
        conversation = AIConversation(
            trigger=AIConversationTrigger(trigger),
            session=session,
            handler_context=handler_context,
            metadata=metadata or {},
        )
        self._replaydb.db.save(conversation)

        if initial_message is not None:
            role = AIMessageRole.user
            text: str
            if isinstance(initial_message, tuple):
                role = AIMessageRole(initial_message[0])
                text = initial_message[1]
            else:
                text = initial_message
            self.append_message(conversation, role=role, text=text)
            refreshed = self.get_conversation(conversation)
            if refreshed is not None:
                return refreshed

        return conversation

    def get_conversation(
        self, conversation: AIConversation | Id | str
    ) -> AIConversation | None:
        conversation_id = self._require_conversation_id(conversation)
        return self._replaydb.db.find_one(
            Model=AIConversation,
            query=eq(AIConversation.id, conversation_id),  # type: ignore[arg-type]
        )

    def append_message(
        self,
        conversation: AIConversation,
        role: AIMessageRole | str,
        text: str,
        source: str | None = None,
    ) -> AIConversationItem:
        conversation = self._require_conversation(conversation)
        item = AIConversationItem(
            conversation=conversation,
            session=conversation.session,
            type=AIConversationItemType.message,
            order=self._next_order(conversation),
            role=AIMessageRole(role),
            content=[AIContentPart(text=text)],
            source=source,
        )
        self._replaydb.db.save(item)
        self._touch_conversation(conversation, item)
        return item

    def append_function_call(
        self,
        conversation: AIConversation,
        call_id: str,
        name: str,
        arguments: dict[str, Any],
        response_id: str | None = None,
    ) -> AIConversationItem:
        conversation = self._require_conversation(conversation)
        item = AIConversationItem(
            conversation=conversation,
            session=conversation.session,
            type=AIConversationItemType.function_call,
            order=self._next_order(conversation),
            call_id=call_id,
            name=name,
            arguments=arguments,
            response_id=response_id,
        )
        self._replaydb.db.save(item)
        self._touch_conversation(conversation, item)
        return item

    def append_function_call_output(
        self,
        conversation: AIConversation,
        call_id: str,
        output: str,
    ) -> AIConversationItem:
        conversation = self._require_conversation(conversation)
        item = AIConversationItem(
            conversation=conversation,
            session=conversation.session,
            type=AIConversationItemType.function_call_output,
            order=self._next_order(conversation),
            call_id=call_id,
            output=output,
        )
        self._replaydb.db.save(item)
        self._touch_conversation(conversation, item)
        return item

    def append_assistant_response(
        self,
        conversation: AIConversation,
        text: str,
        response_id: str | None,
        model: str | None,
    ) -> AIConversationItem:
        conversation = self._require_conversation(conversation)
        item = AIConversationItem(
            conversation=conversation,
            session=conversation.session,
            type=AIConversationItemType.message,
            order=self._next_order(conversation),
            role=AIMessageRole.assistant,
            content=[AIContentPart(text=text)],
            response_id=response_id,
            response_model=model,
        )
        self._replaydb.db.save(item)
        self._touch_conversation(conversation, item)
        return item

    def list_items(
        self, conversation: AIConversation | Id | str, included_only: bool = True
    ) -> list[AIConversationItem]:
        conversation_id = self._require_conversation_id(conversation)
        query = eq(AIConversationItem.conversation, conversation_id)  # type: ignore[arg-type]
        if included_only:
            query = query & eq(AIConversationItem.included_in_context, True)  # type: ignore[arg-type]

        return cast(
            list[AIConversationItem],
            self._replaydb.db.find_many(
                Model=AIConversationItem,
                query=query,
                sort=sort((AIConversationItem.order, 1)),  # type: ignore[arg-type]
            ),
        )

    def close_conversation(self, conversation: AIConversation) -> None:
        conversation = self._require_conversation(conversation)
        conversation.status = AIConversationStatus.closed
        conversation.closed_at = conversation.updated_at
        self._replaydb.db.save(conversation)

    def record_response(
        self,
        conversation: AIConversation,
        response: Any,
        streamed: bool = False,
    ) -> AIResponseRecord:
        conversation = self._require_conversation(conversation)
        response_data = _to_dict(response)
        response_id = response_data.get("id") or response_data.get("response_id")

        if response_id is not None:
            existing = self._replaydb.db.find_one(
                Model=AIResponseRecord,
                query=AIResponseRecord.response_id == response_id,
            )
            if existing is not None:
                return existing

        usage = _to_dict(response_data.get("usage"))
        input_tokens = int(usage.get("input_tokens") or 0)
        cached_tokens = int(
            _get_nested(usage, "input_tokens_details", "cached_tokens", default=0) or 0
        )
        output_tokens = int(usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
        metadata = {
            "response": {
                key: value
                for key, value in response_data.items()
                if key not in {"usage"}
            }
        }

        record = AIResponseRecord(
            conversation=conversation,
            session=conversation.session,
            response_id=response_id,
            model=response_data.get("model"),
            status=response_data.get("status"),
            streamed=streamed,
            input_tokens=input_tokens,
            cached_tokens=cached_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            raw_usage=usage or None,
            metadata=metadata,
        )
        self._replaydb.db.save(record)
        conversation.last_response_id = response_id
        conversation.total_input_tokens += input_tokens
        conversation.total_cached_tokens += cached_tokens
        conversation.total_output_tokens += output_tokens
        conversation.total_tokens += total_tokens
        conversation.total_cost += record.total_cost
        self._replaydb.db.save(conversation)
        return record

    def _next_order(self, conversation: AIConversation) -> int:
        conversation_id = self._require_conversation_id(conversation)
        latest = self._replaydb.db.find_one(
            Model=AIConversationItem,
            query=eq(AIConversationItem.conversation, conversation_id),  # type: ignore[arg-type]
            sort=sort((AIConversationItem.order, -1)),  # type: ignore[arg-type]
        )
        if latest is None:
            return 0
        return int(latest.order) + 1

    def _touch_conversation(
        self, conversation: AIConversation, item: AIConversationItem
    ) -> None:
        conversation = self._require_conversation(conversation)
        conversation.last_item_at = item.created_at
        conversation.item_count += 1
        self._replaydb.db.save(conversation)

    def delete_conversations(self, conversations: list[AIConversation]) -> None:
        if not conversations:
            return
        for conversation in conversations:
            conversation_id = self._require_conversation_id(conversation)
            item_query = eq(AIConversationItem.conversation, conversation_id)  # type: ignore[arg-type]
            conversation_query = eq(AIConversation.id, conversation_id)  # type: ignore[arg-type]
            self._replaydb.db.delete(AIConversationItem, query=item_query)
            self._replaydb.db.delete(AIConversation, query=conversation_query)

    def delete_response_records(self, response_records: list[AIResponseRecord]) -> None:
        if not response_records:
            return
        for response_record in response_records:
            response_id = self._require_response_record_id(response_record)
            response_query = eq(AIResponseRecord.id, response_id)  # type: ignore[arg-type]
            self._replaydb.db.delete(AIResponseRecord, query=response_query)

    def _require_conversation(
        self, conversation: AIConversation | Id | str
    ) -> AIConversation:
        conversation_id = self._require_conversation_id(conversation)
        found = self.get_conversation(conversation)
        if found is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        return found

    def _require_conversation_id(self, conversation: AIConversation | Id | str) -> Id:
        if isinstance(conversation, str):
            return cast(Id, conversation)
        if not isinstance(conversation, AIConversation):
            return conversation
        if conversation.id is None:
            raise ValueError("Conversation must be saved before use")
        return conversation.id

    def _require_response_record_id(self, response_record: AIResponseRecord) -> Id:
        if response_record.id is None:
            raise ValueError("Response record must be saved before deletion")
        return response_record.id


conversation_store = ConversationStore()
