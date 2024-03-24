from replays import ReplayReader, time2secs, db, replaydb
from os.path import join
from replays.types import AssistantMessage, Metadata, Role
from datetime import datetime, timedelta
from pyodmongo.queries import eq

FIXTURE_DIR = "tests/fixtures"


def test_replay_typing():
    reader = ReplayReader()

    raw_replay = reader.load_replay_raw("tests/fixtures/Equilibrium LE (84).SC2Replay")

    replay = reader.to_typed_replay(raw_replay)

    assert replay.map_name == "Equilibrium LE"


def test_default_projection_time():
    reader = ReplayReader()

    fixture = "Equilibrium LE (84).SC2Replay"

    raw_replay = reader.load_replay_raw(join(FIXTURE_DIR, fixture))

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


def test_default_projection_chrono():
    fixture = "Radhuset Station LE (85) ZvP chrono.SC2Replay"

    reader = ReplayReader()
    raw_replay = reader.load_replay_raw(join(FIXTURE_DIR, fixture))

    replay = reader.to_typed_replay(raw_replay)

    default_projection = replay.default_projection()

    assert all(
        "is_chronoboosted" not in bo or bo["is_chronoboosted"] == True
        for bo in default_projection["players"][0]["build_order"]
    )


def test_default_projection_workers():
    fixture = "Radhuset Station LE (85) ZvP chrono.SC2Replay"

    workers = ["Drone", "Probe", "SCV"]

    reader = ReplayReader()
    raw_replay = reader.load_replay_raw(join(FIXTURE_DIR, fixture))

    replay = reader.to_typed_replay(raw_replay)

    default_projection = replay.default_projection(include_workers=False)

    worker_in_bo = [
        bo["name"] not in workers or "is_chronoboosted" in bo
        for bo in default_projection["players"][0]["build_order"]
    ]
    assert all(worker_in_bo)


def test_add_metadata():
    reader = ReplayReader()

    rep = "Site Delta LE (106) ZvZ 2base Muta into mass muta chaotic win.SC2Replay"

    replay = reader.load_replay(join(FIXTURE_DIR, rep))

    meta = Metadata(
        replay=replay.id,
    )
    meta.description = "This is a test description 3"
    meta.conversation = [
        AssistantMessage(
            **{"created_at": datetime.now(), "role": Role.user, "text": "Hello"}
        ),
        AssistantMessage(
            **{
                "created_at": datetime.now() + timedelta(seconds=1),
                "role": Role.assistant,
                "text": "Hi there!",
            }
        ),
    ]

    meta.tags = ["test", "zvz", "muta"]

    replaydb.db.save(meta, query=eq(Metadata.replay, replay.id))

    db.save(meta, query=eq(Metadata.replay, replay.id))
