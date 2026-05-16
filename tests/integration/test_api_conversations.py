from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.persistence.conversation_store import (
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
