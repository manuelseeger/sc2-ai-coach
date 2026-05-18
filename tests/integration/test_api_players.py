from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from src.persistence.conversation_store import ConversationStore
from src.persistence.replay_store import Alias, PlayerInfo
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
def test_get_player_returns_json_without_binary_portrait_fields(
    seeded_replay_mongo_container,
) -> None:
    app = _create_app(seeded_replay_mongo_container)
    player = PlayerInfo(
        id="2-S2-1-123456",
        toon_handle="2-S2-1-123456",
        name="KnownOpponent",
        portrait=b"primary-bytes",
        portrait_constructed=b"constructed-bytes",
        aliases=[Alias(name="KnownAlias", portraits=[b"alias-portrait-bytes"])],
        tags=["tag-a"],
    )
    seeded_replay_mongo_container.replay_store.upsert(player)

    with TestClient(app) as client:
        response = client.get(f"/api/players/{player.toon_handle}")

    assert response.status_code == 200
    assert response.json() == {
        "id": player.toon_handle,
        "toon_handle": player.toon_handle,
        "name": "KnownOpponent",
        "aliases": [{"name": "KnownAlias", "seen_on": None}],
        "tags": ["tag-a"],
    }


@pytest.mark.mongo
def test_player_list_query_crud_and_relationship_routes_follow_documented_contract(
    seeded_replay_mongo_container,
) -> None:
    app = _create_app(seeded_replay_mongo_container)
    replay = seeded_replay_mongo_container.seeded_replays[0]
    replay_player = replay.players[0]

    create_payload = {
        "id": replay_player.toon_handle,
        "toon_handle": replay_player.toon_handle,
        "name": replay_player.name,
        "aliases": [
            {
                "name": "PracticeAlias",
                "portraits": [],
                "seen_on": None,
            }
        ],
        "tags": ["ladder"],
    }

    with TestClient(app) as client:
        created = client.post("/api/players", json=create_payload)
        listed = client.get(
            "/api/players",
            params={"q": "PracticeAlias", "tag": "ladder", "docs_per_page": 20},
        )
        queried = client.post(
            "/api/players/query",
            json={
                "filter": {"toon_handle": replay_player.toon_handle},
                "sort": {"name": 1},
                "current_page": 1,
                "docs_per_page": 10,
            },
        )
        aliases = client.get(f"/api/players/{replay_player.toon_handle}/aliases")
        related_replays = client.get(
            f"/api/players/{replay_player.toon_handle}/replays",
            params={"docs_per_page": 10},
        )
        patched = client.patch(
            f"/api/players/{replay_player.toon_handle}",
            json={"name": "UpdatedName", "tags": ["reviewed"]},
        )

        replace_payload = dict(create_payload)
        replace_payload["name"] = "ReplacementName"
        replace_payload["aliases"] = [{"name": "ReplacementAlias", "portraits": []}]
        replaced = client.put(
            f"/api/players/{replay_player.toon_handle}",
            json=replace_payload,
        )

        deleted = client.delete(f"/api/players/{replay_player.toon_handle}")
        missing = client.get(f"/api/players/{replay_player.toon_handle}")
        replay_players = client.get(f"/api/replays/{replay.id}/players")

    assert created.status_code == 200
    assert created.json()["id"] == replay_player.toon_handle

    assert listed.status_code == 200
    assert listed.json()["docs_quantity"] == 1
    assert listed.json()["docs"][0] == {
        "id": replay_player.toon_handle,
        "toon_handle": replay_player.toon_handle,
        "name": replay_player.name,
        "aliases": [{"name": "PracticeAlias", "seen_on": None}],
        "tags": ["ladder"],
    }

    assert queried.status_code == 200
    assert [doc["id"] for doc in queried.json()["docs"]] == [replay_player.toon_handle]

    assert aliases.status_code == 200
    assert aliases.json() == [{"name": "PracticeAlias", "seen_on": None}]

    assert related_replays.status_code == 200
    assert [doc["id"] for doc in related_replays.json()["docs"]] == [replay.id]

    assert patched.status_code == 200
    assert patched.json()["name"] == "UpdatedName"
    assert patched.json()["tags"] == ["reviewed"]

    assert replaced.status_code == 200
    assert replaced.json()["name"] == "ReplacementName"
    assert replaced.json()["aliases"] == [{"name": "ReplacementAlias", "seen_on": None}]

    assert deleted.status_code == 204
    assert missing.status_code == 404
    assert missing.json() == {
        "error": {
            "code": "not_found",
            "message": "Document not found",
            "details": {"resource": "players", "id": replay_player.toon_handle},
        }
    }

    assert replay_players.status_code == 200
    linked = next(
        item
        for item in replay_players.json()
        if item["replay_player"]["toon_handle"] == replay_player.toon_handle
    )
    assert linked["player_info"] is None


@pytest.mark.mongo
def test_player_portrait_metadata_helpers_and_media_routes_follow_documented_contract(
    seeded_replay_mongo_container,
) -> None:
    app = _create_app(seeded_replay_mongo_container)
    primary_player = PlayerInfo(
        id="2-S2-1-123456",
        toon_handle="2-S2-1-123456",
        name="PortraitPlayer",
        portrait=b"primary-portrait",
        portrait_constructed=b"constructed-portrait",
        aliases=[
            Alias(
                name="AliasOne", portraits=[b"alias-portrait-a", b"alias-portrait-b"]
            ),
            Alias(name="AliasTwo", portraits=[]),
        ],
        tags=["portraits"],
    )
    secondary_player = PlayerInfo(
        id="2-S2-1-654321",
        toon_handle="2-S2-1-654321",
        name="NoPortraitPlayer",
        aliases=[Alias(name="AliasOnly", portraits=[])],
        tags=["portraits"],
    )
    seeded_replay_mongo_container.replay_store.upsert(primary_player)
    seeded_replay_mongo_container.replay_store.upsert(secondary_player)

    with TestClient(app) as client:
        single = client.get(
            f"/api/players/{primary_player.toon_handle}/portrait-metadata"
        )
        bulk = client.post(
            "/api/players/portrait-metadata",
            json={
                "toon_handles": [
                    "2-S2-1-000000",
                    primary_player.toon_handle,
                    primary_player.toon_handle,
                    secondary_player.toon_handle,
                ]
            },
        )
        portrait = client.get(f"/api/players/{primary_player.toon_handle}/portrait")
        constructed = client.get(
            f"/api/players/{primary_player.toon_handle}/portrait/constructed"
        )
        alias_portrait = client.get(
            f"/api/players/{primary_player.toon_handle}/aliases/0/portraits/1"
        )
        missing_constructed = client.get(
            f"/api/players/{secondary_player.toon_handle}/portrait/constructed"
        )

    assert single.status_code == 200
    assert single.json() == {
        "toon_handle": primary_player.toon_handle,
        "portrait": {
            "available": True,
            "url": f"/api/players/{primary_player.toon_handle}/portrait",
        },
        "portrait_constructed": {
            "available": True,
            "url": f"/api/players/{primary_player.toon_handle}/portrait/constructed",
        },
        "aliases": [
            {
                "index": 0,
                "name": "AliasOne",
                "portraits": [
                    {
                        "index": 0,
                        "available": True,
                        "url": f"/api/players/{primary_player.toon_handle}/aliases/0/portraits/0",
                    },
                    {
                        "index": 1,
                        "available": True,
                        "url": f"/api/players/{primary_player.toon_handle}/aliases/0/portraits/1",
                    },
                ],
            },
            {
                "index": 1,
                "name": "AliasTwo",
                "portraits": [],
            },
        ],
    }

    assert bulk.status_code == 200
    assert bulk.json() == {
        "items": [
            single.json(),
            {
                "toon_handle": secondary_player.toon_handle,
                "portrait": {
                    "available": False,
                    "url": f"/api/players/{secondary_player.toon_handle}/portrait",
                },
                "portrait_constructed": {
                    "available": False,
                    "url": f"/api/players/{secondary_player.toon_handle}/portrait/constructed",
                },
                "aliases": [
                    {
                        "index": 0,
                        "name": "AliasOnly",
                        "portraits": [],
                    }
                ],
            },
        ]
    }

    assert portrait.status_code == 200
    assert portrait.headers["content-type"] == "image/png"
    assert portrait.content == b"primary-portrait"

    assert constructed.status_code == 200
    assert constructed.headers["content-type"] == "image/png"
    assert constructed.content == b"constructed-portrait"

    assert alias_portrait.status_code == 200
    assert alias_portrait.headers["content-type"] == "image/png"
    assert alias_portrait.content == b"alias-portrait-b"

    assert missing_constructed.status_code == 404
