import sys

import parametrize_from_file
import pytest

if sys.gettrace() is None:
    pytest.skip("Skipping debug-only LLM test.", allow_module_level=True)

from coach import AISession
from replays.reader import ReplayReader
from tests.critic import LmmCritic


@parametrize_from_file(indirect=["replay_file"])
def test_analyze_replay(
    replay_file, instructions, convo, critic: LmmCritic, sc2api_mock
):
    # arrange
    reader = ReplayReader()
    session = AISession()

    replay = reader.load_replay(replay_file)
    session.initiate_from_new_replay(replay)
    response = session.stream_conversation()

    critic.init(instructions=instructions)

    # act
    for entry in convo:
        question, criteria, expected = entry.values()

        response = session.chat(question)

        # assert
        c = f"QUESTION: {question}\nANSWER: {response}"
        critique = critic.evaluate(c, criteria)
        print(f"PASSED: {critique.passed}")
        print(critique.justification)
        assert critique.passed == expected
