from __future__ import annotations

from datetime import datetime

from pymongo import MongoClient

from src.api.config import ApiConfig
from src.api.contracts import ConversationListResponse, ConversationSummary
from src.api.conversation_types import AIConversationStatus, AIConversationTrigger


class ConversationQueryService:
    def __init__(self, config: ApiConfig):
        self._config = config

    @property
    def collection(self):
        client = MongoClient(str(self._config.mongo_dsn))
        return client.get_database(self._config.db_name).get_collection(
            "ai_conversations"
        )

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
        document = self.collection.find_one({"_id": conversation_id})
        if document is None:
            return None
        return _conversation_summary(document)


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


def _required_datetime(value: datetime | None) -> datetime:
    if value is None:
        raise ValueError("Conversation is missing created_at")
    return value
