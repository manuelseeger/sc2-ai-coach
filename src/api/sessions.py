from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient
from pyodmongo import Id

from src.api.config import ApiConfig
from src.api.contracts import (
    ConversationListResponse,
    ConversationSummary,
    SessionDetailResponse,
    SessionListItem,
    SessionListResponse,
    SessionSummaryResponse,
)
from src.api.conversation_types import AIConversationStatus, AIConversationTrigger


class SessionQueryService:
    def __init__(self, config: ApiConfig):
        self._config = config
        self._client = MongoClient(str(config.mongo_dsn))

    @property
    def database(self):
        return self._client.get_database(self._config.db_name)

    @property
    def collection(self):
        return self.database.get_collection("sessions")

    @property
    def conversation_collection(self):
        return self.database.get_collection("ai_conversations")

    @property
    def item_collection(self):
        return self.database.get_collection("ai_conversation_items")

    @property
    def response_collection(self):
        return self.database.get_collection("ai_responses")

    def list_sessions(
        self,
        *,
        page: int,
        page_size: int,
        ai_backend: str | None,
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> SessionListResponse:
        query: dict[str, Any] = {}
        if ai_backend is not None:
            query["ai_backend"] = ai_backend
        date_query: dict[str, datetime] = {}
        if from_date is not None:
            date_query["$gte"] = from_date
        if to_date is not None:
            date_query["$lte"] = to_date
        if date_query:
            query["session_date"] = date_query

        documents = list(self.collection.find(query))
        documents.sort(key=lambda document: _required_datetime(document.get("session_date")), reverse=True)

        total = len(documents)
        start = (page - 1) * page_size
        page_documents = documents[start : start + page_size]

        return SessionListResponse(
            items=[self._session_list_item(document) for document in page_documents],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=_total_pages(total, page_size),
        )

    def get_session_detail(self, session_id: str) -> SessionDetailResponse | None:
        document = self.collection.find_one(_session_id_query(session_id))
        if document is None:
            return None
        conversation_ids = [
            str(item.get("_id"))
            for item in self.conversation_collection.find(
                {"session": {"$in": _possible_id_values(session_id)}},
                {"_id": 1},
            )
            if item.get("_id") is not None
        ]
        return _session_detail(document, conversation_ids=conversation_ids)

    def get_session_conversations(
        self, session_id: str
    ) -> ConversationListResponse | None:
        session = self.collection.find_one(_session_id_query(session_id))
        if session is None:
            return None

        documents = list(
            self.conversation_collection.find({"session": {"$in": _possible_id_values(session_id)}})
        )
        documents.sort(key=_conversation_activity_sort_key, reverse=True)

        return ConversationListResponse(
            items=[_conversation_summary(document) for document in documents],
            page=1,
            page_size=50,
            total=len(documents),
            total_pages=1 if documents else 0,
            available_statuses=list(AIConversationStatus),
            available_triggers=list(AIConversationTrigger),
        )

    def get_session_summary(self, session_id: str) -> SessionSummaryResponse | None:
        session = self.collection.find_one(_session_id_query(session_id))
        if session is None:
            return None

        conversation_documents = list(
            self.conversation_collection.find({"session": {"$in": _possible_id_values(session_id)}})
        )
        conversation_ids = [document.get("_id") for document in conversation_documents if document.get("_id") is not None]
        response_documents = list(
            self.response_collection.find(
                {"session": {"$in": _possible_id_values(session_id)}},
                {
                    "input_tokens": 1,
                    "output_tokens": 1,
                    "total_tokens": 1,
                    "total_cost": 1,
                },
            )
        )

        item_count = 0
        if conversation_ids:
            item_count = self.item_collection.count_documents(
                {"conversation": {"$in": _identifier_variants(conversation_ids)}}
            )

        return SessionSummaryResponse(
            session_id=str(session.get("_id")),
            conversation_count=len(conversation_documents),
            item_count=item_count,
            response_count=len(response_documents),
            total_input_tokens=sum(int(document.get("input_tokens") or 0) for document in response_documents),
            total_output_tokens=sum(int(document.get("output_tokens") or 0) for document in response_documents),
            total_tokens=sum(int(document.get("total_tokens") or 0) for document in response_documents),
            total_cost=sum(float(document.get("total_cost") or 0) for document in response_documents),
        )

    def _session_list_item(self, document: dict[str, Any]) -> SessionListItem:
        session_id = str(document.get("_id"))
        conversation_count = self.conversation_collection.count_documents(
            {"session": {"$in": _possible_id_values(session_id)}}
        )
        return SessionListItem(
            id=session_id,
            detail_path=f"/sessions/{session_id}",
            session_date=_required_datetime(document.get("session_date")),
            ai_backend=str(document.get("ai_backend")),
            conversation_count=conversation_count,
            current_conversation_id=_optional_id(document.get("current_conversation")),
            total_cost=float(document.get("total_cost") or 0),
        )


def _session_detail(
    document: dict[str, Any], *, conversation_ids: list[str]
) -> SessionDetailResponse:
    session_id = str(document.get("_id"))
    return SessionDetailResponse(
        id=session_id,
        detail_path=f"/sessions/{session_id}",
        session_date=_required_datetime(document.get("session_date")),
        ai_backend=str(document.get("ai_backend")),
        current_conversation_id=_optional_id(document.get("current_conversation")),
        twitch_conversation_id=_optional_id(document.get("twitch_conversation")),
        conversation_ids=conversation_ids,
        total_input_tokens=int(document.get("total_input_tokens") or 0),
        total_cached_tokens=int(document.get("total_cached_tokens") or 0),
        total_output_tokens=int(document.get("total_output_tokens") or 0),
        total_tokens=int(document.get("total_tokens") or 0),
        total_cost=float(document.get("total_cost") or 0),
    )


def _conversation_summary(document: dict[str, Any]) -> ConversationSummary:
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


def _session_id_query(session_id: str) -> dict[str, Any]:
    return {"_id": {"$in": _possible_id_values(session_id)}}


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


def _identifier_variants(values: list[object]) -> list[object]:
    unique_values: list[object] = []
    for value in values:
        for candidate in _possible_id_values(str(value)):
            if candidate not in unique_values:
                unique_values.append(candidate)
    return unique_values


def _optional_id(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _required_datetime(value: datetime | None) -> datetime:
    if value is None:
        raise ValueError("Session is missing required datetime field")
    return value


def _conversation_activity_sort_key(document: dict[str, Any]) -> datetime:
    created_at = _required_datetime(document.get("created_at"))
    return document.get("last_item_at") or created_at


def _total_pages(total: int, page_size: int) -> int:
    if total == 0:
        return 0
    return (total + page_size - 1) // page_size