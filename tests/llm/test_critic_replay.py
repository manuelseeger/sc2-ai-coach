import parametrize_from_file
import pytest

from coach import AISession
from replays.reader import ReplayReader
from tests.mocks import MicMock, TranscriberMock, TTSMock


@pytest.mark.parametrize(
    "replay_file",
    [
        "Solaris LE (179) ZvP ground hydra lurker.SC2Replay",
    ],
    indirect=["replay_file"],
)
def test_init_from_replay_with_metadata(prompt_file, replay_file, mocker):
    reader = ReplayReader()
    session = AISession()

    user_convo = [
        "At what time did the protoss build their first 2 ground units?",
        "At what time did they take their third base?",
        "What did they spend their first 3 chronoboosts on?",
        "Thank you, that will be all for now.",
    ]
    mocker.patch("coach.mic", MicMock())
    mocker.patch("coach.tts", TTSMock())
    mocker.patch("coach.transcriber", TranscriberMock(data=user_convo))

    rep = "Solaris LE (179) ZvP ground hydra lurker.SC2Replay"

    replay = reader.load_replay(replay_file)
    session.handle_new_replay(__name__, replay)

    session.close()
