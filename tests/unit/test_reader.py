import pytest
import sc2reader

from replays.reader import ReplayReader
from replays.sc2readerplugins.ReplayStats import is_gg, player_worker_micro
from replays.util import time2secs


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
            {0: (1, 1), 1: (0, 0)},
        )
    ],
    indirect=["replay_file"],
)
def test_replaystats_worker_micro(replay_file, expected):
    replay = sc2reader.load_replay(replay_file)
    micro = player_worker_micro(replay)
    assert micro == expected
