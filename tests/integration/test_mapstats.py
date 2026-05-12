import pytest
from rich import print

from src.persistence.replay_store import get_replay_store
from src.replays.types import Replay
from tests.conftest import load_test_settings

replay_store = get_replay_store()


def test_get_map_stats_for_map():
    from src.mapstats import MatchupsByMap

    runtime_settings = load_test_settings()

    for map_name in runtime_settings.ladder_maps:
        q = Replay.map_name == map_name

        maps: list[MatchupsByMap] = replay_store.db.find_many(
            Model=MatchupsByMap, query=q
        )

        print(maps)
        assert len(maps) > 0, map_name
        assert len(maps[0].matchups) > 0, map_name


def test_get_season_map_stats():
    from src.mapstats import get_map_stats

    runtime_settings = load_test_settings()

    for map_name in runtime_settings.ladder_maps:
        stats = get_map_stats(map_name)

        assert stats is not None, map_name
        assert stats.matchups is not None, map_name
        assert len(stats.matchups) > 0, map_name
        print(stats)


def test_write_map_stats():
    from src.mapstats import update_map_stats

    map_name = "Taito Citadel LE"
    update_map_stats(map_name)
