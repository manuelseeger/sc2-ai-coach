from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from src.persistence.conversation_store import ConversationStore
from src.persistence.replay_store import PlayerInfo
from src.persistence.runtime import PersistenceServices
from src.persistence.session_store import SessionStore


def _create_app(seeded_replay_mongo_container):
    api_app = importlib.import_module("src.api.app")
    database = seeded_replay_mongo_container.database
    runtime_settings = seeded_replay_mongo_container.settings
    replay_store = seeded_replay_mongo_container.replay_store

    return api_app.create_app(
        settings_loader=lambda: runtime_settings,
        persistence_builder=lambda _settings: PersistenceServices(
            database=database,
            replay_store=replay_store,
            conversation_store=ConversationStore(database),
            session_store=SessionStore(database),
        ),
    )


@pytest.mark.mongo
def test_list_and_get_replays_use_replay_ids(
    seeded_replay_mongo_container,
) -> None:
    app = _create_app(seeded_replay_mongo_container)
    expected = sorted(
        seeded_replay_mongo_container.seeded_replays,
        key=lambda replay: replay.date,
        reverse=True,
    )

    with TestClient(app) as client:
        listed = client.get("/api/replays")
        fetched = client.get(f"/api/replays/{expected[0].id}")

    assert listed.status_code == 200
    body = listed.json()
    assert body["docs_quantity"] == len(expected)
    assert body["docs"][0]["id"] == expected[0].id
    assert body["docs"][1]["id"] == expected[1].id

    assert fetched.status_code == 200
    assert fetched.json()["id"] == expected[0].id
    assert fetched.json()["map_name"] == expected[0].map_name


@pytest.mark.mongo
def test_replay_crud_and_query_cover_documented_replay_routes(
    seeded_replay_mongo_container,
) -> None:
    app = _create_app(seeded_replay_mongo_container)
    seed = seeded_replay_mongo_container.seeded_replays[0]
    create_payload = seed.model_dump(mode="json")
    create_payload["id"] = "f" * 64
    create_payload["filename"] = "created-api-replay.SC2Replay"

    with TestClient(app) as client:
        created = client.post("/api/replays", json=create_payload)
        listed = client.get(
            "/api/replays",
            params={
                "player": seed.players[0].name[:4],
                "map": seed.map_name[:4],
                "docs_per_page": 100,
            },
        )
        queried = client.post(
            "/api/replays/query",
            json={
                "filter": {"filename": create_payload["filename"]},
                "sort": {"date": -1},
                "current_page": 1,
                "docs_per_page": 10,
            },
        )
        patched = client.patch(
            f"/api/replays/{create_payload['id']}",
            json={"filename": "patched-api-replay.SC2Replay"},
        )

        replace_payload = dict(create_payload)
        replace_payload["filename"] = "replaced-api-replay.SC2Replay"
        replaced = client.put(f"/api/replays/{create_payload['id']}", json=replace_payload)
        deleted = client.delete(f"/api/replays/{create_payload['id']}")
        missing = client.get(f"/api/replays/{create_payload['id']}")

    assert created.status_code == 200
    assert created.json()["id"] == create_payload["id"]
    assert created.json()["filename"] == "created-api-replay.SC2Replay"

    assert listed.status_code == 200
    listed_ids = {doc["id"] for doc in listed.json()["docs"]}
    assert create_payload["id"] in listed_ids

    assert queried.status_code == 200
    assert [doc["id"] for doc in queried.json()["docs"]] == [create_payload["id"]]

    assert patched.status_code == 200
    assert patched.json()["filename"] == "patched-api-replay.SC2Replay"

    assert replaced.status_code == 200
    assert replaced.json()["filename"] == "replaced-api-replay.SC2Replay"

    assert deleted.status_code == 204
    assert missing.status_code == 404
    assert missing.json() == {
        "error": {
            "code": "not_found",
            "message": "Document not found",
            "details": {"resource": "replays", "id": create_payload["id"]},
        }
    }


@pytest.mark.mongo
def test_replay_create_and_replace_reject_invalid_raw_json(
    seeded_replay_mongo_container,
) -> None:
    app = _create_app(seeded_replay_mongo_container)
    seed = seeded_replay_mongo_container.seeded_replays[0]
    create_payload = seed.model_dump(mode="json")
    create_payload["id"] = "1" * 64
    create_payload.pop("filename")

    replace_payload = seed.model_dump(mode="json")
    replace_payload["filename"] = 42

    with TestClient(app) as client:
        invalid_create = client.post("/api/replays", json=create_payload)
        invalid_replace = client.put(f"/api/replays/{seed.id}", json=replace_payload)

    assert invalid_create.status_code == 422
    assert invalid_create.json()["error"]["code"] == "validation_error"

    assert invalid_replace.status_code == 422
    assert invalid_replace.json()["error"]["code"] == "validation_error"


@pytest.mark.mongo
def test_replay_metadata_relationship_routes_and_replay_delete_cascade(
    seeded_replay_mongo_container,
) -> None:
    app = _create_app(seeded_replay_mongo_container)
    replay = seeded_replay_mongo_container.seeded_replays[0]

    with TestClient(app) as client:
        replaced = client.put(
            f"/api/replays/{replay.id}/metadata",
            json={
                "replay": replay.id,
                "description": "Replay-level note from relationship route.",
                "tags": ["relationship", "macro"],
                "replay_summary_conversation": None,
            },
        )
        fetched = client.get(f"/api/replays/{replay.id}/metadata")
        patched = client.patch(
            f"/api/replays/{replay.id}/metadata",
            json={
                "description": "Updated replay-level note.",
                "tags": ["patched"],
            },
        )
        deleted = client.delete(f"/api/replays/{replay.id}")
        missing_metadata = client.get(f"/api/metadata/{replaced.json()['id']}")

    assert replaced.status_code == 200
    assert replaced.json()["replay"] == replay.id
    assert replaced.json()["description"] == "Replay-level note from relationship route."

    assert fetched.status_code == 200
    assert fetched.json()["id"] == replaced.json()["id"]

    assert patched.status_code == 200
    assert patched.json()["description"] == "Updated replay-level note."
    assert patched.json()["tags"] == ["patched"]

    assert deleted.status_code == 204
    assert missing_metadata.status_code == 404
    assert missing_metadata.json() == {
        "error": {
            "code": "not_found",
            "message": "Document not found",
            "details": {"resource": "metadata", "id": replaced.json()["id"]},
        }
    }


@pytest.mark.mongo
def test_get_replay_metadata_returns_missing_metadata_404_when_replay_exists(
    seeded_replay_mongo_container,
) -> None:
    app = _create_app(seeded_replay_mongo_container)
    replay = seeded_replay_mongo_container.seeded_replays[0]

    with TestClient(app) as client:
        response = client.get(f"/api/replays/{replay.id}/metadata")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Document not found",
            "details": {"resource": "metadata", "id": replay.id},
        }
    }


@pytest.mark.mongo
def test_replay_players_route_returns_embedded_players_with_known_player_records(
    seeded_replay_mongo_container,
) -> None:
    app = _create_app(seeded_replay_mongo_container)
    replay = seeded_replay_mongo_container.seeded_replays[0]
    known_player = replay.players[0]
    seeded_replay_mongo_container.replay_store.upsert(
        PlayerInfo(
            id=known_player.toon_handle,
            toon_handle=known_player.toon_handle,
            name=known_player.name,
            tags=["known-player"],
        )
    )

    with TestClient(app) as client:
        response = client.get(f"/api/replays/{replay.id}/players")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == len(replay.players)

    linked = next(
        item for item in payload if item["replay_player"]["toon_handle"] == known_player.toon_handle
    )
    assert linked["player_info"] is not None
    assert linked["player_info"]["id"] == known_player.toon_handle
    assert linked["player_info"]["name"] == known_player.name

    missing = [item for item in payload if item["replay_player"]["toon_handle"] != known_player.toon_handle]
    assert any(item["player_info"] is None for item in missing)