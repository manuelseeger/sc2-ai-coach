from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from src.persistence.conversation_store import ConversationStore
from src.persistence.database import MongoDatabase
from src.persistence.replay_store import ReplayStore
from src.persistence.runtime import PersistenceServices
from src.persistence.session_store import SessionStore
from src.runtime.settings import Config


def _create_app(
    *,
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
):
    api_app = importlib.import_module("src.api.app")
    return api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=lambda _settings: PersistenceServices(
            database=mongo_database,
            replay_store=replay_store,
            conversation_store=conversation_store,
            session_store=session_store,
        ),
    )


def _create_metadata(client: TestClient, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "replay": "a" * 64,
        "description": "Early pool pressure with no worker scout.",
        "tags": ["aggression", "scouting-gap"],
        "replay_summary_conversation": None,
    }
    payload.update(overrides)

    response = client.post("/api/metadata", json=payload)
    assert response.status_code == 200
    return response.json()


@pytest.mark.mongo
def test_create_and_get_metadata_round_trip_uses_metadata_model(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    app = _create_app(
        mongo_database=mongo_database,
        runtime_settings=runtime_settings,
        replay_store=replay_store,
        conversation_store=conversation_store,
        session_store=session_store,
    )

    payload = {
        "replay": "a" * 64,
        "description": "Early pool pressure with no worker scout.",
        "tags": ["aggression", "scouting-gap"],
        "replay_summary_conversation": None,
    }

    with TestClient(app) as client:
        created = client.post("/api/metadata", json=payload)

        assert created.status_code == 200
        created_body = created.json()
        assert created_body["replay"] == payload["replay"]
        assert created_body["description"] == payload["description"]
        assert created_body["tags"] == payload["tags"]
        assert isinstance(created_body["id"], str)

        fetched = client.get(f"/api/metadata/{created_body['id']}")

    assert fetched.status_code == 200
    assert fetched.json() == created_body


@pytest.mark.mongo
def test_list_metadata_supports_pagination_sort_and_documented_filters(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    app = _create_app(
        mongo_database=mongo_database,
        runtime_settings=runtime_settings,
        replay_store=replay_store,
        conversation_store=conversation_store,
        session_store=session_store,
    )

    with TestClient(app) as client:
        _create_metadata(
            client,
            replay="a" * 64,
            description="B - Ling flood scout timing",
            tags=["aggression"],
        )
        expected = _create_metadata(
            client,
            replay="b" * 64,
            description="A - Macro opener with summary",
            tags=["macro", "creep"],
            replay_summary_conversation="conversation-1",
        )
        _create_metadata(
            client,
            replay="c" * 64,
            description="C - Late game lurker setup",
            tags=["macro", "lurker"],
        )

        response = client.get(
            "/api/metadata",
            params={
                "current_page": 1,
                "docs_per_page": 5,
                "sort": "description",
                "tag": "macro",
                "has_summary": "true",
                "replay": "b" * 64,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["current_page"] == 1
    assert body["docs_quantity"] == 1
    assert [doc["id"] for doc in body["docs"]] == [expected["id"]]
    assert body["docs"][0]["description"] == "A - Macro opener with summary"


@pytest.mark.mongo
def test_metadata_query_is_paginated_and_rejects_write_operators(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    app = _create_app(
        mongo_database=mongo_database,
        runtime_settings=runtime_settings,
        replay_store=replay_store,
        conversation_store=conversation_store,
        session_store=session_store,
    )

    with TestClient(app) as client:
        _create_metadata(
            client,
            replay="d" * 64,
            description="A - Macro hatch first",
            tags=["macro"],
        )
        _create_metadata(
            client,
            replay="e" * 64,
            description="B - Macro hydra bust",
            tags=["macro", "hydra"],
        )

        response = client.post(
            "/api/metadata/query",
            json={
                "filter": {"tags": "macro"},
                "sort": {"description": 1},
                "current_page": 1,
                "docs_per_page": 1,
            },
        )
        rejected = client.post(
            "/api/metadata/query",
            json={"filter": {"$set": {"description": "oops"}}},
        )

    assert response.status_code == 200
    assert response.json()["docs_quantity"] == 2
    assert [doc["description"] for doc in response.json()["docs"]] == [
        "A - Macro hatch first"
    ]

    assert rejected.status_code == 400
    assert rejected.json() == {
        "error": {
            "code": "malformed_filter",
            "message": "MongoDB write operators are not allowed in query filters.",
            "details": {"operator": "$set"},
        }
    }


@pytest.mark.mongo
def test_patch_replace_delete_metadata_and_missing_document_errors_use_error_envelope(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    app = _create_app(
        mongo_database=mongo_database,
        runtime_settings=runtime_settings,
        replay_store=replay_store,
        conversation_store=conversation_store,
        session_store=session_store,
    )

    with TestClient(app) as client:
        created = _create_metadata(
            client,
            replay="f" * 64,
            description="Original metadata",
            tags=["initial"],
        )

        patched = client.patch(
            f"/api/metadata/{created['id']}",
            json={
                "description": "Patched metadata",
                "tags": ["patched", "follow-up"],
            },
        )
        replaced = client.put(
            f"/api/metadata/{created['id']}",
            json={
                "id": created["id"],
                "replay": "f" * 64,
                "description": "Replaced metadata",
                "tags": ["replacement"],
                "replay_summary_conversation": "conversation-2",
            },
        )
        operator_patch = client.patch(
            f"/api/metadata/{created['id']}",
            json={"$set": {"description": "nope"}},
        )
        deleted = client.delete(f"/api/metadata/{created['id']}")
        missing = client.get(f"/api/metadata/{created['id']}")

    assert patched.status_code == 200
    assert patched.json()["description"] == "Patched metadata"
    assert patched.json()["tags"] == ["patched", "follow-up"]

    assert replaced.status_code == 200
    assert replaced.json()["description"] == "Replaced metadata"
    assert replaced.json()["tags"] == ["replacement"]
    assert replaced.json()["replay_summary_conversation"] == "conversation-2"

    assert operator_patch.status_code == 400
    assert operator_patch.json() == {
        "error": {
            "code": "invalid_patch",
            "message": "Patch bodies cannot use MongoDB update operators.",
            "details": {"operator": "$set"},
        }
    }

    assert deleted.status_code == 204
    assert missing.status_code == 404
    assert missing.json() == {
        "error": {
            "code": "not_found",
            "message": "Document not found",
            "details": {"resource": "metadata", "id": created["id"]},
        }
    }


@pytest.mark.mongo
def test_replace_metadata_with_invalid_body_id_returns_validation_error_envelope(
    mongo_database: MongoDatabase,
    runtime_settings: Config,
    replay_store: ReplayStore,
    conversation_store: ConversationStore,
    session_store: SessionStore,
) -> None:
    app = _create_app(
        mongo_database=mongo_database,
        runtime_settings=runtime_settings,
        replay_store=replay_store,
        conversation_store=conversation_store,
        session_store=session_store,
    )

    with TestClient(app) as client:
        created = _create_metadata(
            client,
            replay="9" * 64,
            description="Original metadata",
            tags=["initial"],
        )

        response = client.put(
            f"/api/metadata/{created['id']}",
            json={
                "id": "new",
                "replay": "9" * 64,
                "description": "Replacement payload",
                "tags": ["replacement"],
                "replay_summary_conversation": None,
            },
        )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed."
    assert isinstance(body["error"]["details"]["errors"], list)
    assert any(error["loc"] == ["body", "id"] for error in body["error"]["details"]["errors"])