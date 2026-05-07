import pytest
from rich import print

from config import config
from src.mapstats import MatchupsByMap, get_map_stats, update_map_stats
from src.persistence.replay_store import get_replay_store
from src.replays.types import Replay

replay_store = get_replay_store()


@pytest.mark.parametrize(
    "map_name",
    config.ladder_maps,
)
def test_get_map_stats_for_map(map_name):
    q = Replay.map_name == map_name

    maps: list[MatchupsByMap] = replay_store.db.find_many(Model=MatchupsByMap, query=q)

    print(maps)
    assert len(maps) > 0
    assert len(maps[0].matchups) > 0


@pytest.mark.parametrize(
    "map_name",
    config.ladder_maps,
)
def test_get_season_map_stats(map_name):
    stats = get_map_stats(map_name)

    assert stats is not None
    assert stats.matchups is not None
    assert len(stats.matchups) > 0
    print(stats)


def test_write_map_stats():
    map_name = config.ladder_maps[0]
    map_name = "Taito Citadel LE"
    update_map_stats(map_name)
