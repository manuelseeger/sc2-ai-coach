from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient
from pyodmongo import Id

from src.api.config import ApiConfig
from src.api.contracts import (
    ConversationDetailResponse,
    ConversationItemsResponse,
    ConversationListResponse,
    ConversationReviewItem,
    ConversationReviewLink,
    ConversationReviewSummary,
    ConversationSummary,
)
from src.api.conversation_types import AIConversationStatus, AIConversationTrigger
from src.replays.types import AIContentPart, AIConversationItemType, AIMessageRole


class ConversationQueryService:
    def __init__(self, config: ApiConfig):
        self._config = config
        self._client = MongoClient(str(config.mongo_dsn))

    @property
    def database(self):
        return self._client.get_database(self._config.db_name)

    @property
    def collection(self):
        return self.database.get_collection("ai_conversations")

    @property
    def item_collection(self):
        return self.database.get_collection("ai_conversation_items")

    def list_conversations(
        self,
        *,
        page: int,
        page_size: int,
        trigger: AIConversationTrigger | None,
        statuses: list[AIConversationStatus],
    ) -> ConversationListResponse:
        query = {"status": {"$in": [status.value for status in statuses]}}
        if trigger is not None:
            query["trigger"] = trigger.value

        documents = list(self.collection.find(query))
        documents.sort(key=_activity_sort_key, reverse=True)

        total = len(documents)
        start = (page - 1) * page_size
        page_documents = documents[start : start + page_size]
        return ConversationListResponse(
            items=[_conversation_summary(document) for document in page_documents],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=_total_pages(total, page_size),
            available_statuses=list(AIConversationStatus),
            available_triggers=list(AIConversationTrigger),
        )

    def get_conversation_summary(
        self, conversation_id: str
    ) -> ConversationSummary | None:
        document = self.collection.find_one(_conversation_id_query(conversation_id))
        if document is None:
            return None
        return _conversation_summary(document)

    def get_conversation_items(
        self,
        conversation_id: str,
        *,
        included_in_context: bool | None,
        include_raw: bool,
    ) -> ConversationItemsResponse | None:
        conversation = self.collection.find_one(_conversation_id_query(conversation_id))
        if conversation is None:
            return None

        query: dict[str, Any] = _conversation_item_query(conversation_id)
        if included_in_context is not None:
            query["included_in_context"] = included_in_context

        documents = list(self.item_collection.find(query).sort([("order", 1)]))
        return ConversationItemsResponse(
            items=_conversation_review_items(documents, include_raw=include_raw)
        )

    def get_conversation_detail(
        self, conversation_id: str
    ) -> ConversationDetailResponse | None:
        conversation = self.collection.find_one(_conversation_id_query(conversation_id))
        if conversation is None:
            return None

        item_documents = list(
            self.item_collection.find(_conversation_item_query(conversation_id)).sort(
                [("order", 1)]
            )
        )
        return ConversationDetailResponse(
            conversation=_conversation_review_summary(conversation),
            items=_conversation_review_items(item_documents, include_raw=False),
        )

    def close_conversation(
        self, conversation_id: str
    ) -> ConversationReviewSummary | None:
        return self._apply_action(conversation_id, action="close")

    def archive_conversation(
        self, conversation_id: str
    ) -> ConversationReviewSummary | None:
        return self._apply_action(conversation_id, action="archive")

    def _apply_action(
        self, conversation_id: str, *, action: str
    ) -> ConversationReviewSummary | None:
        conversation = self.collection.find_one(_conversation_id_query(conversation_id))
        if conversation is None:
            return None

        updated = dict(conversation)
        status = AIConversationStatus(updated["status"])

        if action == "close":
            if status != AIConversationStatus.active:
                raise ValueError("Conversation can only be closed while active.")
            updated["status"] = AIConversationStatus.closed.value
            updated["closed_at"] = datetime.now(UTC)
        elif action == "archive":
            if status == AIConversationStatus.archived:
                raise ValueError("Conversation is already archived.")
            updated["status"] = AIConversationStatus.archived.value
        else:
            raise ValueError(f"Unsupported action: {action}")

        self.collection.update_one(
            {"_id": conversation["_id"]},
            {"$set": {"status": updated["status"], "closed_at": updated.get("closed_at")}},
        )
        return _conversation_review_summary(updated)


def _conversation_summary(document: dict) -> ConversationSummary:
    conversation_id = str(document.get("_id"))
    created_at = _required_datetime(document.get("created_at"))
    last_item_at = document.get("last_item_at")
    activity_at = last_item_at or created_at
    return ConversationSummary(
        id=conversation_id,
        detail_path=f"/conversations/{conversation_id}",
        trigger=AIConversationTrigger(document["trigger"]),
        status=AIConversationStatus(document["status"]),
        item_count=int(document.get("item_count") or 0),
        created_at=created_at,
        activity_at=activity_at,
        last_item_at=last_item_at,
        replay_id=_optional_id(document.get("replay_id")),
        session_id=_optional_id(document.get("session")),
    )


def _conversation_review_summary(document: dict) -> ConversationReviewSummary:
    conversation_id = str(document.get("_id"))
    return ConversationReviewSummary(
        id=conversation_id,
        detail_path=f"/conversations/{conversation_id}",
        trigger=AIConversationTrigger(document["trigger"]),
        status=AIConversationStatus(document["status"]),
        item_count=int(document.get("item_count") or 0),
        created_at=_required_datetime(document.get("created_at")),
        replay=_review_link(document.get("replay_id"), "/replays"),
        session=_review_link(document.get("session"), "/sessions"),
    )


def _conversation_review_items(
    documents: list[dict[str, Any]], *, include_raw: bool
) -> list[ConversationReviewItem]:
    tool_names_by_call_id: dict[str, str] = {}
    items: list[ConversationReviewItem] = []

    for document in documents:
        call_id = _optional_id(document.get("call_id"))
        tool_name = _optional_name(document.get("name"))
        if call_id is not None and tool_name is not None:
            tool_names_by_call_id[call_id] = tool_name

        if tool_name is None and call_id is not None:
            tool_name = tool_names_by_call_id.get(call_id)

        items.append(
            ConversationReviewItem(
                id=str(document.get("_id")),
                kind=AIConversationItemType(document["type"]),
                created_at=_required_datetime(document.get("created_at")),
                role=_optional_role(document.get("role")),
                message_text=_message_text(document.get("content")),
                tool_name=tool_name,
                tool_arguments=_tool_arguments(document.get("arguments")),
                tool_output=_tool_output(document.get("output")),
                included_in_context=bool(document.get("included_in_context", True)),
                raw_item=document.get("raw_item") if include_raw else None,
            )
        )

    return items


def _activity_sort_key(document: dict) -> datetime:
    created_at = _required_datetime(document.get("created_at"))
    return document.get("last_item_at") or created_at


def _total_pages(total: int, page_size: int) -> int:
    if total == 0:
        return 0
    return (total + page_size - 1) // page_size


def _optional_id(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_name(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_role(value: object) -> AIMessageRole | None:
    if value is None:
        return None
    return AIMessageRole(str(value))


def _tool_arguments(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    return dict(value)


def _tool_output(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _message_text(value: object) -> str | None:
    if value is None:
        return None

    parts: list[str] = []
    for item in value:
        if isinstance(item, AIContentPart):
            parts.append(item.text)
            continue

        if isinstance(item, dict):
            text = item.get("text")
            if text is not None:
                parts.append(str(text))

    if not parts:
        return None
    return "\n\n".join(parts)


def _review_link(value: object, prefix: str) -> ConversationReviewLink | None:
    identifier = _optional_id(value)
    if identifier is None:
        return None
    return ConversationReviewLink(id=identifier, path=f"{prefix}/{identifier}")


def _conversation_id_query(conversation_id: str) -> dict[str, Any]:
    return {"_id": {"$in": _possible_id_values(conversation_id)}}


def _conversation_item_query(conversation_id: str) -> dict[str, Any]:
    return {"conversation": {"$in": _possible_id_values(conversation_id)}}


def _possible_id_values(value: str) -> list[object]:
    values: list[object] = [value]

    try:
        values.append(Id(value))
    except Exception:
        pass

    try:
        values.append(ObjectId(value))
    except (InvalidId, TypeError):
        pass

    unique_values: list[object] = []
    for candidate in values:
        if candidate not in unique_values:
            unique_values.append(candidate)
    return unique_values


def _required_datetime(value: datetime | None) -> datetime:
    if value is None:
        raise ValueError("Conversation is missing created_at")
    return value
