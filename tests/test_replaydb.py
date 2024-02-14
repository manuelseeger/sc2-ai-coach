from replays import ReplayDB, time2secs
from os.path import join

FIXTURE_DIR = "tests/fixtures"


def test_replay_typing():
    db = ReplayDB()

    raw_replay = db.load_replay_raw("tests/fixtures/Equilibrium LE (84).SC2Replay")

    replay = db.to_typed_replay(raw_replay)

    replay_json = replay.json()

    assert replay.map_name == "Equilibrium LE"


def test_default_projection_time():
    db = ReplayDB()

    fixture = "Equilibrium LE (84).SC2Replay"

    raw_replay = db.load_replay_raw(join(FIXTURE_DIR, fixture))

    replay = db.to_typed_replay(raw_replay)

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


def test_default_projection_chrono():
    fixture = "Radhuset Station LE (85) ZvP chrono.SC2Replay"

    db = ReplayDB()
    raw_replay = db.load_replay_raw(join(FIXTURE_DIR, fixture))

    replay = db.to_typed_replay(raw_replay)

    default_projection = replay.default_projection()

    assert all(
        "is_chronoboosted" not in bo or bo["is_chronoboosted"] == True
        for bo in default_projection["players"][0]["build_order"]
    )


def test_add_metadata():
    db = ReplayDB()

    rep = "Site Delta LE (106) ZvZ 2base Muta into mass muta chaotic win.SC2Replay"

    raw_replay = db.load_replay_raw(f"tests/fixtures/{rep}")

    replay = db.to_typed_replay(raw_replay)

    metadata = replay.add_metadata()

    assert "build" not in metadata
    assert "players" in metadata
    assert "name" in metadata["players"][0]
    assert "sid" in metadata["players"][0]
    assert all(
        time2secs(bo["time"]) <= 100 for bo in metadata["players"][0]["build_order"]
    )
