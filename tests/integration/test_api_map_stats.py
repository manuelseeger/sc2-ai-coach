from __future__ import annotations

import importlib
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from persistence.conversation_store import ConversationStore
from persistence.runtime import PersistenceServices
from persistence.session_store import SessionStore


def _create_app(seeded_replay_mongo_container):
    api_app = importlib.import_module("api.app")
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


def _expected_map_stats(
    replays,
    *,
    student_name: str,
    student_race: str,
    map_name: str | None = None,
    min_date=None,
):
    expected: dict[str, dict[str, dict[str, int]]] = {}

    for replay in replays:
        if map_name is not None and replay.map_name != map_name:
            continue
        if min_date is not None and replay.date < min_date:
            continue

        student = next(
            (player for player in replay.players if player.name == student_name), None
        )
        if student is None or student.play_race != student_race:
            continue

        opponent = next(
            player for player in replay.players if player.name != student_name
        )
        matchup = f"{student.play_race}v{opponent.play_race}"
        bucket = expected.setdefault(replay.map_name, {}).setdefault(
            matchup,
            {"totalGames": 0, "wins": 0, "losses": 0},
        )
        bucket["totalGames"] += 1
        if student.result == "Win":
            bucket["wins"] += 1
        if student.result == "Loss":
            bucket["losses"] += 1

    return expected


def _serialized_map_stats(expected):
    return [
        {
            "map": map_name,
            "matchups": [
                {
                    "matchup": matchup,
                    "totalGames": totals["totalGames"],
                    "wins": totals["wins"],
                    "losses": totals["losses"],
                    "winrate": totals["wins"] / totals["totalGames"],
                }
                for matchup, totals in sorted(matchups.items())
            ],
        }
        for map_name, matchups in sorted(expected.items())
    ]


@pytest.mark.mongo
def test_list_map_stats_returns_aggregation_backed_results_for_exact_map_filter(
    seeded_replay_mongo_container,
) -> None:
    app = _create_app(seeded_replay_mongo_container)
    target_map = seeded_replay_mongo_container.seeded_replays[0].map_name
    expected = _expected_map_stats(
        seeded_replay_mongo_container.seeded_replays,
        student_name=seeded_replay_mongo_container.settings.student.name,
        student_race=seeded_replay_mongo_container.settings.student.race,
        map_name=target_map,
    )

    with TestClient(app) as client:
        response = client.get("/api/map-stats", params={"map": target_map})

    assert response.status_code == 200
    assert response.json() == _serialized_map_stats(expected)


@pytest.mark.mongo
def test_get_map_stats_by_name_applies_inclusive_min_date_filter(
    seeded_replay_mongo_container,
) -> None:
    app = _create_app(seeded_replay_mongo_container)
    target_replay = seeded_replay_mongo_container.seeded_replays[0]
    expected = _expected_map_stats(
        seeded_replay_mongo_container.seeded_replays,
        student_name=seeded_replay_mongo_container.settings.student.name,
        student_race=seeded_replay_mongo_container.settings.student.race,
        map_name=target_replay.map_name,
        min_date=target_replay.date,
    )

    with TestClient(app) as client:
        response = client.get(
            f"/api/map-stats/{target_replay.map_name}",
            params={"min_date": target_replay.date.isoformat()},
        )

    assert response.status_code == 200
    assert response.json() == _serialized_map_stats(expected)[0]


@pytest.mark.mongo
def test_get_map_stats_by_name_returns_404_when_filter_removes_all_grouped_results(
    seeded_replay_mongo_container,
) -> None:
    app = _create_app(seeded_replay_mongo_container)
    target_replay = seeded_replay_mongo_container.seeded_replays[0]

    with TestClient(app) as client:
        response = client.get(
            f"/api/map-stats/{target_replay.map_name}",
            params={
                "min_date": (target_replay.date + timedelta(days=3650)).isoformat()
            },
        )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Document not found",
            "details": {"resource": "map-stats", "id": target_replay.map_name},
        }
    }
