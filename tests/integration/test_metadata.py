import pytest

from aicoach.aicoach_mock import AICoachMock as AICoach
from replays import ReplayReader
from replays.metadata import safe_replay_summary


@pytest.mark.parametrize(
    "replay_file",
    [
        "Site Delta LE (106) ZvZ 2base Muta into mass muta chaotic win.SC2Replay",
    ],
    indirect=True,
)
def test_save_replay_summary(replay_file):

    coach = AICoach()
    coach.create_thread()

    data = [
        "On a 2 player map, the Zerg player opened with a 2 base Muta build, transitioning into mass Mutas. The game was chaotic, but the Zerg player won.",
        "2 player map, ZvZ, 2 base Muta, mass Muta, chaotic win",
    ]
    coach.set_data(data)

    reader = ReplayReader()

    replay = reader.load_replay(replay_file)

    safe_replay_summary(replay, coach)
