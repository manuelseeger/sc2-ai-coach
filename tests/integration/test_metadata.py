import pytest

from aicoach.aicoach_mock import AICoachMock as AICoach
from aicoach.functions import AddMetadata
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


@pytest.mark.parametrize(
    "replay_id, tags",
    [
        (
            "684ace3ae5e9e40efe50342b1f7ab15611a0bbdbcc03cfc4b2e2b908b35e0a70",
            "2 rax reaper",
        ),
    ],
)
def test_function_meta_to_existing(replay_id, tags):
    response = AddMetadata(replay_id=replay_id, tags=tags)
    assert response is True
