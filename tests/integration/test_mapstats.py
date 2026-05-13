from __future__ import annotations

from src.replays.types import Replay


def test_matchups_by_map_aggregates_seeded_replays_in_fresh_container(
    seeded_replay_mongo_container,
):
    from src.mapstats import MatchupsByMap, _configure_matchups_pipeline

    runtime_settings = seeded_replay_mongo_container.settings
    replay_store = seeded_replay_mongo_container.replay_store
    seeded_replays = seeded_replay_mongo_container.seeded_replays
    _configure_matchups_pipeline(runtime_settings)

    expected_maps = sorted(
        {
            replay.map_name
            for replay in seeded_replays
            if any(
                player.name == runtime_settings.student.name
                for player in replay.players
            )
            and replay.get_player(runtime_settings.student.name).play_race
            == runtime_settings.student.race
        }
    )

    assert expected_maps

    for map_name in expected_maps:
        maps: list[MatchupsByMap] = replay_store.db.find_many(
            Model=MatchupsByMap,
            query=Replay.map_name == map_name,
        )

        assert len(maps) == 1, map_name
        assert maps[0].map == map_name
        assert maps[0].matchups, map_name
