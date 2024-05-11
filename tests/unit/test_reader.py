from replays import ReplayReader, time2secs
import pytest


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
