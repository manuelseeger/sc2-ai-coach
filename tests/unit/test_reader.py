import pytest

import sc2reader
from src.replays.plugins.ReplayStats import is_gg, player_worker_micro
from src.replays.reader import ReplayReader
from src.util import time2secs
from tests.conftest import load_test_settings, only_in_debugging


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
    assert (
        replay.id == "3966c5a1c6e15e84e63e033e54783c74b1ccb78bc9194b47bb6fb11f0ada64c6"
    )
    assert replay.id == raw_replay.filehash
    assert len(replay.players) == 2

    player_one, player_two = replay.players

    assert player_one.name == "FuRoar"
    assert player_one.pid == 1
    assert player_one.pick_race == "Protoss"
    assert player_one.play_race == "Protoss"
    assert player_one.result == "Loss"
    assert player_one.uid == 0
    assert player_one.toon_id == 9928025
    assert player_one.toon_handle == "2-S2-1-9928025"
    assert player_one.url == "https://starcraft2.com/en-us/profile/2/1/9928025"
    assert player_one.highest_league == 5
    assert player_one.scaled_rating == 3965
    assert player_one.build_order
    assert player_one.stats.avg_unspent_resources == pytest.approx(778.4645669291339)
    assert player_one.worker_stats.worker_trained_total == 106

    assert player_two.name == "zatic"
    assert player_two.pid == 2
    assert player_two.pick_race == "Zerg"
    assert player_two.play_race == "Zerg"
    assert player_two.result == "Win"
    assert player_two.uid == 1
    assert player_two.toon_id == 691545
    assert player_two.toon_handle == "2-S2-1-691545"
    assert player_two.url == "https://starcraft2.com/en-us/profile/2/1/691545"
    assert player_two.highest_league == 5
    assert player_two.scaled_rating == 3701
    assert player_two.build_order


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
        "Equilibrium LE (84).SC2Replay",
    ],
    indirect=True,
)
def test_default_projection_id(replay_file):
    reader = ReplayReader()
    raw_replay = reader.load_replay_raw(replay_file)

    replay = reader.to_typed_replay(raw_replay)

    default_projection = replay.default_projection()

    assert "_id" not in default_projection
    assert "id" in default_projection
    assert len(default_projection["id"]) == 64


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
        "is_chronoboosted" not in bo or bo["is_chronoboosted"] is True
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
    "replay_file",
    [
        "El Dorado ZvP glave into DT.SC2Replay",
    ],
    indirect=True,
)
def test_default_projection_stats(replay_file):
    reader = ReplayReader()
    replay = reader.load_replay(replay_file)

    default_projection = replay.default_projection()

    assert "stats" in default_projection
    assert "stats" in default_projection["players"][0]

    assert all(
        "unspent_resources" not in player["stats"]
        for player in default_projection["players"]
    )
    assert all(
        "worker_active" not in player["stats"]
        for player in default_projection["players"]
    )


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
def test_replay_reader_enables_spending_quotient_plugin(replay_file):
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
def test_replay_reader_enables_player_stats_tracker_plugin(replay_file):
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


@pytest.mark.parametrize(
    "replay_file",
    [
        "Amygdala (69) AFK player.SC2Replay",
    ],
    indirect=True,
)
def test_afk_replay(replay_file):
    reader = ReplayReader()

    replay = reader.load_replay(replay_file)

    assert any([p.avg_apm == 0 for p in replay.players])


@pytest.mark.parametrize(
    "replay_file",
    [
        "Tokamak LE (6) ZvT 2 base Terran push against gasless.SC2Replay",
    ],
    indirect=True,
)
def test_replay_colors_positions(replay_file):
    runtime_settings = load_test_settings()
    reader = ReplayReader()

    replay_raw = reader.load_replay_raw(replay_file)

    replay = reader.to_typed_replay(replay_raw)

    p1, p2 = replay.players

    assert p1.color.name.lower() == "red"
    assert p2.color.name.lower() == "blue"

    if runtime_settings.include_map_details:
        assert p1.clock_position == 1
        assert p2.clock_position == 7
    else:
        assert p1.clock_position is None
        assert p2.clock_position is None
