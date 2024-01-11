from replays import ReplayDB, time2secs


def test_replay_typing():
    db = ReplayDB()

    raw_replay = db.load_replay_raw("tests/fixtures/Equilibrium LE (84).SC2Replay")

    replay = db.to_typed_replay(raw_replay)

    replay_json = replay.json()

    assert replay.map_name == "Equilibrium LE"


def test_default_projection():
    db = ReplayDB()

    raw_replay = db.load_replay_raw("tests/fixtures/Equilibrium LE (84).SC2Replay")

    replay = db.to_typed_replay(raw_replay)
    
    limit = 100

    default_projection = replay.default_projection(limit=limit)

    assert "build" not in default_projection
    assert "players" in default_projection
    assert "name" in default_projection["players"][0]
    assert "sid" not in default_projection["players"][0]
    assert all(time2secs(bo["time"]) <= limit for bo in default_projection["players"][0]['build_order'])
