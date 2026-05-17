from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.persistence.conversation_store import (
    AIConversationStatus,
    AIConversationTrigger,
    AIMessageRole,
    AIResponseRecord,
    ConversationStore,
)
from src.persistence.database import MongoDatabase
from src.persistence.replay_store import ReplayStore
from src.persistence.runtime import PersistenceServices
from src.persistence.session_store import SessionStore
from src.runtime.settings import Config


@pytest.mark.mongo
def test_get_conversations_returns_paginated_recent_first_results_and_typed_filters(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    session = session_store.create(
        session_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ai_backend=runtime_settings.aibackend,
        completion_pricing=0.0,
        prompt_pricing=0.0,
    )

    older = conversation_store.create_conversation(
        trigger=AIConversationTrigger.wake,
        session=session,
        initial_message="older",
        metadata={"scope": "conversation-list", "position": "older"},
    )
    newer = conversation_store.create_conversation(
        trigger=AIConversationTrigger.wake,
        session=session,
        initial_message="newer",
        metadata={"scope": "conversation-list", "position": "newer"},
    )
    closed = conversation_store.create_conversation(
        trigger=AIConversationTrigger.twitch_chat,
        session=session,
        initial_message="closed",
        metadata={"scope": "conversation-list", "position": "closed"},
    )
    closed.status = AIConversationStatus.closed

    base_time = datetime(2026, 1, 3, tzinfo=timezone.utc)
    older.created_at = base_time
    newer.created_at = base_time + timedelta(minutes=5)
    closed.created_at = base_time + timedelta(minutes=10)
    conversation_store.save(older)
    conversation_store.save(newer)
    conversation_store.save(closed)

    api_app = importlib.import_module("src.api.app")
    app = api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=lambda _settings: PersistenceServices(
            database=mongo_database,
            replay_store=replay_store,
            conversation_store=conversation_store,
            session_store=session_store,
        ),
    )

    with TestClient(app) as client:
        listed = client.get(
            "/api/conversations",
            params={"session": str(session.id), "docs_per_page": 10},
        )
        filtered = client.get(
            "/api/conversations",
            params={
                "session": str(session.id),
                "trigger": AIConversationTrigger.wake.value,
                "status": AIConversationStatus.active.value,
                "docs_per_page": 10,
            },
        )

    assert listed.status_code == 200
    assert listed.json()["docs_quantity"] == 3
    assert [doc["id"] for doc in listed.json()["docs"]] == [
        str(closed.id),
        str(newer.id),
        str(older.id),
    ]

    assert filtered.status_code == 200
    assert [doc["id"] for doc in filtered.json()["docs"]] == [
        str(newer.id),
        str(older.id),
    ]


@pytest.mark.mongo
def test_get_conversation_items_returns_full_ordered_flow_and_supports_included_filter(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    conversation = conversation_store.create_conversation(
        trigger=AIConversationTrigger.wake,
        initial_message="hello",
        metadata={"test_scope": "api_conversations"},
    )
    included_item = conversation_store.append_message(
        conversation,
        role=AIMessageRole.assistant,
        text="hi",
    )
    excluded_item = conversation_store.append_message(
        conversation,
        role=AIMessageRole.system,
        text="hidden from model context",
    )
    excluded_item.included_in_context = False
    excluded_item.raw_item = {"kind": "excluded"}
    conversation_store.save(excluded_item)

    api_app = importlib.import_module("src.api.app")
    app = api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=lambda _settings: PersistenceServices(
            database=mongo_database,
            replay_store=replay_store,
            conversation_store=conversation_store,
            session_store=session_store,
        ),
    )

    with TestClient(app) as client:
        response = client.get(f"/api/conversations/{conversation.id}/items")

        assert response.status_code == 200
        assert [item["order"] for item in response.json()] == [0, 1, 2]
        assert [item["role"] for item in response.json()] == [
            "user",
            "assistant",
            "system",
        ]
        assert response.json()[2]["included_in_context"] is False
        assert response.json()[2]["raw_item"] == {"kind": "excluded"}

        included_only = client.get(
            f"/api/conversations/{conversation.id}/items",
            params={"included_in_context": True},
        )

        assert included_only.status_code == 200
        assert [item["order"] for item in included_only.json()] == [0, 1]
        assert [item["role"] for item in included_only.json()] == ["user", "assistant"]

        excluded_only = client.get(
            f"/api/conversations/{conversation.id}/items",
            params={"included_in_context": False},
        )

    assert excluded_only.status_code == 200
    assert [item["id"] for item in excluded_only.json()] == [str(excluded_item.id)]


@pytest.mark.mongo
def test_get_conversation_returns_persisted_conversation_document(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    conversation = conversation_store.create_conversation(
        trigger=AIConversationTrigger.wake,
        initial_message="hello",
        metadata={"test_scope": "api_conversation_detail"},
    )

    api_app = importlib.import_module("src.api.app")
    app = api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=lambda _settings: PersistenceServices(
            database=mongo_database,
            replay_store=replay_store,
            conversation_store=conversation_store,
            session_store=session_store,
        ),
    )

    with TestClient(app) as client:
        response = client.get(f"/api/conversations/{conversation.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(conversation.id)
    assert response.json()["trigger"] == "wake"
    assert response.json()["status"] == "active"
    assert response.json()["item_count"] == 1
    assert response.json()["metadata"] == {"test_scope": "api_conversation_detail"}


@pytest.mark.mongo
def test_get_conversation_responses_returns_full_ordered_response_timeline(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    conversation = conversation_store.create_conversation(
        trigger=AIConversationTrigger.wake,
        initial_message="hello",
        metadata={"test_scope": "api_conversation_responses"},
    )
    other_conversation = conversation_store.create_conversation(
        trigger=AIConversationTrigger.wake,
        initial_message="other",
        metadata={"test_scope": "api_conversation_responses_other"},
    )
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first_record = conversation_store.save(
        AIResponseRecord(
            conversation=conversation.id,
            response_id="resp-conv-1",
            model="gpt-5.4",
            status="completed",
            created_at=base_time + timedelta(seconds=10),
            total_tokens=11,
            total_cost=0.01,
            metadata={"step": 1},
        )
    )
    second_record = conversation_store.save(
        AIResponseRecord(
            conversation=conversation.id,
            response_id="resp-conv-2",
            model="gpt-5.4",
            status="completed",
            created_at=base_time + timedelta(seconds=20),
            total_tokens=22,
            total_cost=0.02,
            metadata={"step": 2},
        )
    )
    conversation_store.save(
        AIResponseRecord(
            conversation=other_conversation.id,
            response_id="resp-other-conv",
            model="gpt-5.4",
            status="completed",
            created_at=base_time + timedelta(seconds=30),
        )
    )

    api_app = importlib.import_module("src.api.app")
    app = api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=lambda _settings: PersistenceServices(
            database=mongo_database,
            replay_store=replay_store,
            conversation_store=conversation_store,
            session_store=session_store,
        ),
    )

    with TestClient(app) as client:
        response = client.get(f"/api/conversations/{conversation.id}/responses")

    assert response.status_code == 200
    assert [record["id"] for record in response.json()] == [
        str(first_record.id),
        str(second_record.id),
    ]
    assert [record["response_id"] for record in response.json()] == [
        "resp-conv-1",
        "resp-conv-2",
    ]
    assert [record["metadata"] for record in response.json()] == [
        {"step": 1},
        {"step": 2},
    ]


@pytest.mark.mongo
def test_conversation_crud_and_query_cover_documented_routes(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    session = session_store.create(
        session_date=datetime(2026, 1, 4, tzinfo=timezone.utc),
        ai_backend=runtime_settings.aibackend,
        completion_pricing=0.0,
        prompt_pricing=0.0,
    )

    create_payload = {
        "session": str(session.id),
        "trigger": AIConversationTrigger.wake.value,
        "status": AIConversationStatus.active.value,
        "title": "Created through API",
        "metadata": {"scope": "conversation-crud", "step": "created"},
    }

    api_app = importlib.import_module("src.api.app")
    app = api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=lambda _settings: PersistenceServices(
            database=mongo_database,
            replay_store=replay_store,
            conversation_store=conversation_store,
            session_store=session_store,
        ),
    )

    with TestClient(app) as client:
        created = client.post("/api/conversations", json=create_payload)
        assert created.status_code == 200
        conversation_id = created.json()["id"]

        queried = client.post(
            "/api/conversations/query",
            json={
                "filter": {"metadata.scope": "conversation-crud"},
                "sort": {"created_at": -1},
                "current_page": 1,
                "docs_per_page": 10,
            },
        )
        patched = client.patch(
            f"/api/conversations/{conversation_id}",
            json={
                "status": AIConversationStatus.closed.value,
                "metadata": {"scope": "conversation-crud", "step": "patched"},
            },
        )

        replace_payload = dict(created.json())
        replace_payload["status"] = AIConversationStatus.active.value
        replace_payload["closed_at"] = "2026-01-05T00:00:00Z"
        replace_payload["title"] = "Replaced through API"
        replace_payload["metadata"] = {
            "scope": "conversation-crud",
            "step": "replaced",
        }
        replaced = client.put(f"/api/conversations/{conversation_id}", json=replace_payload)
        deleted = client.delete(f"/api/conversations/{conversation_id}")
        missing = client.get(f"/api/conversations/{conversation_id}")

    assert queried.status_code == 200
    assert [doc["id"] for doc in queried.json()["docs"]] == [conversation_id]

    assert patched.status_code == 200
    assert patched.json()["status"] == "closed"
    assert patched.json()["closed_at"] is not None
    assert patched.json()["metadata"] == {
        "scope": "conversation-crud",
        "step": "patched",
    }

    assert replaced.status_code == 200
    assert replaced.json()["status"] == "active"
    assert replaced.json()["closed_at"] is None
    assert replaced.json()["title"] == "Replaced through API"

    assert deleted.status_code == 204
    assert missing.status_code == 404


@pytest.mark.mongo
def test_append_conversation_item_assigns_server_order_and_rejects_path_mismatch(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    conversation = conversation_store.create_conversation(
        trigger=AIConversationTrigger.wake,
        initial_message="hello",
        metadata={"scope": "conversation-append"},
    )
    other = conversation_store.create_conversation(
        trigger=AIConversationTrigger.repl,
        initial_message="other",
        metadata={"scope": "conversation-append-other"},
    )

    api_app = importlib.import_module("src.api.app")
    app = api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=lambda _settings: PersistenceServices(
            database=mongo_database,
            replay_store=replay_store,
            conversation_store=conversation_store,
            session_store=session_store,
        ),
    )

    with TestClient(app) as client:
        appended = client.post(
            f"/api/conversations/{conversation.id}/items",
            json={
                "conversation": str(conversation.id),
                "type": "message",
                "role": "assistant",
                "content": [{"text": "follow-up from api"}],
                "order": 99,
                "included_in_context": True,
            },
        )
        mismatch = client.post(
            f"/api/conversations/{conversation.id}/items",
            json={
                "conversation": str(other.id),
                "type": "message",
                "role": "assistant",
                "content": [{"text": "wrong conversation"}],
                "order": 5,
                "included_in_context": True,
            },
        )
        ordered_items = client.get(f"/api/conversations/{conversation.id}/items")

    assert appended.status_code == 200
    assert appended.json()["order"] == 1
    assert appended.json()["content"][0]["text"] == "follow-up from api"

    assert mismatch.status_code == 409
    assert mismatch.json() == {
        "error": {
            "code": "conflict",
            "message": "Path id and body conversation id must match.",
            "details": {
                "resource": "conversation-items",
                "path_id": str(conversation.id),
            },
        }
    }

    assert ordered_items.status_code == 200
    assert [item["order"] for item in ordered_items.json()] == [0, 1]
