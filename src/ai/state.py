from __future__ import annotations

from typing import Any, TypeVar, cast

from pyodmongo import Id
from pyodmongo.queries import eq, sort

from src.replaydb.db import replaydb
from src.replaydb.types import (
    AIContentPart,
    AIConversation,
    AIConversationItem,
    AIConversationItemType,
    AIConversationTrigger,
    AIMessageRole,
    AIResponseRecord,
    Session,
)

ModelT = TypeVar("ModelT")


class ConversationStore:
    def __init__(self):
        self._replaydb = replaydb
        self.db = replaydb.db

    def create_conversation(
        self,
        trigger: AIConversationTrigger | str,
        session: Session | None = None,
        initial_message: str | tuple[AIMessageRole | str, str] | None = None,
        handler_context: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AIConversation:
        conversation = self._save(
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
        self._save(conversation)

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
                query=AIResponseRecord.response_id == record.response_id,
            )
            if existing is not None:
                return existing

        self._save(record)
        conversation.add_response_record(record)
        self._save(conversation)

        session = self._session(conversation.session)
        if session is not None:
            session.add_response_record(record)
            self._save(session)

        return record

    def _next_order(self, conversation: AIConversation) -> int:
        latest = self.db.find_one(
            Model=AIConversationItem,
            query=eq(AIConversationItem.conversation, self._id(conversation)),  # type: ignore[arg-type]
            sort=sort((AIConversationItem.order, -1)),  # type: ignore[arg-type]
        )
        if latest is None:
            return 0
        return int(latest.order) + 1

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

    def _append_item(
        self,
        conversation: AIConversation | Id | str,
        **fields: Any,
    ) -> AIConversationItem:
        conversation = self._conversation(conversation)
        item = self._save(
            AIConversationItem(
                conversation=conversation,
                session=conversation.session,
                order=self._next_order(conversation),
                **fields,
            )
        )
        conversation.add_item(item)
        self._save(conversation)
        return item

    def _conversation(self, conversation: AIConversation | Id | str) -> AIConversation:
        found = self.get_conversation(conversation)
        if found is None:
            raise ValueError(f"Conversation {self._id(conversation)} not found")
        return found

    def _session(self, session: Session | Id | None) -> Session | None:
        if session is None:
            return None
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

    def _save(self, model: ModelT) -> ModelT:
        self.db.save(model)
        return model


conversation_store = ConversationStore()
