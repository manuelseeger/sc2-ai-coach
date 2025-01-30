import pytest
import sc2reader

from src.replaydb.plugins.ReplayStats import is_gg, player_worker_micro
from src.replaydb.reader import ReplayReader
from src.replaydb.util import time2secs
from tests.conftest import only_in_debugging


@pytest.mark.parametrize(
    "replay_file",
    [
        "Equilibrium LE (84).SC2Replay",
    ],
    indirect=True,
)
def test_replay_typing(replay_file):
    reader = ReplayReader()

    raw_replay = reader.load_replay_raw(replay_file)

    replay = reader.to_typed_replay(raw_replay)

    assert replay.map_name == "Equilibrium LE"


@pytest.mark.parametrize(
    "replay_file",
    [
        "Equilibrium LE (84).SC2Replay",
    ],
    indirect=True,
)
def test_default_projection_time(replay_file):
    reader = ReplayReader()

    raw_replay = reader.load_replay_raw(replay_file)

    replay = reader.to_typed_replay(raw_replay)

    limit = 100

    default_projection = replay.default_projection(limit=limit)

    assert "build" not in default_projection
    assert "players" in default_projection
    assert "name" in default_projection["players"][0]
    assert "sid" not in default_projection["players"][0]
    assert all(
        time2secs(bo["time"]) <= limit
        for bo in default_projection["players"][0]["build_order"]
    )


@pytest.mark.parametrize(
    "replay_file",
    [
        "Radhuset Station LE (85) ZvP chrono.SC2Replay",
    ],
    indirect=True,
)
def test_default_projection_chrono(replay_file):

    reader = ReplayReader()
    raw_replay = reader.load_replay_raw(replay_file)

    replay = reader.to_typed_replay(raw_replay)

    default_projection = replay.default_projection()

    assert all(
        "is_chronoboosted" not in bo or bo["is_chronoboosted"] == True
        for bo in default_projection["players"][0]["build_order"]
    )


@pytest.mark.parametrize(
    "replay_file",
    [
        "Radhuset Station LE (85) ZvP chrono.SC2Replay",
    ],
    indirect=True,
)
def test_default_projection_workers(replay_file):

    workers = ["Drone", "Probe", "SCV"]

    reader = ReplayReader()
    raw_replay = reader.load_replay_raw(replay_file)

    replay = reader.to_typed_replay(raw_replay)

    default_projection = replay.default_projection(include_workers=False)

    worker_in_bo = [
        bo["name"] not in workers or "is_chronoboosted" in bo
        for bo in default_projection["players"][0]["build_order"]
    ]
    assert all(worker_in_bo)


@pytest.mark.parametrize(
    "message,expected",
    [
        ("ggwp", True),
        ("fu", False),
        ("ggggg", True),
        ("bg", False),
        ("gg", True),
        ("GG", True),
    ],
)
def test_is_gg(message, expected):
    result = is_gg(message)
    assert result == expected


@pytest.mark.parametrize(
    "replay_file,expected",
    [
        (
            "Goldenaura LE (282) 2 base Terran tank allin.SC2Replay",
            {0: (1, 2), 1: (0, 0)},
        )
    ],
    indirect=["replay_file"],
)
def test_replaystats_worker_micro(replay_file, expected):
    replay = sc2reader.load_replay(replay_file)
    micro = player_worker_micro(replay)
    assert micro == expected


@pytest.mark.parametrize(
    "replay_file",
    [
        "NeoHumanity LE (279) Division By Zero.SC2Replay",
    ],
    indirect=True,
)
def test_apm_tracker_division_by_zero(replay_file):

    reader = ReplayReader()

    replay_raw = reader.load_replay_raw(replay_file)

    p1, p2 = replay_raw.players

    assert p1.avg_apm == 0
    assert p2.avg_apm == 0


@pytest.mark.parametrize(
    "replay_file",
    [
        "Equilibrium LE (84).SC2Replay",
    ],
    indirect=True,
)
def test_worker_tracker(replay_file):
    reader = ReplayReader()

    replay = reader.load_replay(replay_file)

    p1, p2 = replay.players

    assert p1.worker_stats.worker_killed_total == p2.worker_stats.worker_lost_total
    assert p1.worker_stats.worker_lost_total == p2.worker_stats.worker_killed_total


@pytest.mark.parametrize(
    "replay_file",
    [
        "Equilibrium LE (84).SC2Replay",
    ],
    indirect=True,
)
def test_spending_quotient(replay_file):
    reader = ReplayReader()

    replay = reader.load_replay(replay_file)

    p1, p2 = replay.players

    assert p1.avg_sq > 10
    assert p2.avg_sq > 10
    assert p1.avg_sq > p2.avg_sq


@pytest.mark.parametrize(
    "replay_file",
    [
        "Equilibrium LE (84).SC2Replay",
    ],
    indirect=True,
)
def test_player_stats_tracker(replay_file):
    reader = ReplayReader()

    replay = reader.load_replay(replay_file)

    p1, p2 = replay.players

    assert p1.stats.avg_unspent_resources > 0
    assert p2.stats.avg_unspent_resources > 0


@only_in_debugging
@pytest.mark.skip(reason="Skip until fix in upstream sc2reader plugins")
@pytest.mark.parametrize(
    "replay_file",
    [
        "Romanticide LE (164) Archon Mode.SC2Replay",
        "Oxide LE (147) Archon Mode.SC2Replay",
    ],
    indirect=True,
)
def test_apm_archon_mode(replay_file):
    reader = ReplayReader()

    replay = reader.load_replay_raw(replay_file)

    p1, p2, p3, p4 = replay.players

    assert p1.avg_apm > 0
    assert p2.avg_apm > 0
    assert p3.avg_apm > 0
    assert p4.avg_apm > 0


@pytest.mark.parametrize(
    "replay_file",
    [
        "Radhuset Station LE (85) ZvP chrono.SC2Replay",
    ],
    indirect=True,
)
def test_parse_chrono_boost(replay_file):
    reader = ReplayReader()

    replay = reader.load_replay(replay_file)

    p1, p2 = replay.players

    assert any(p.is_chronoboosted for p in p1.build_order)
