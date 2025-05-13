import parametrize_from_file

from coach import AISession
from src.replaydb.reader import ReplayReader
from tests.conftest import only_in_debugging
from tests.critic import LmmCritic


@only_in_debugging
@parametrize_from_file(indirect=["replay_file"])
def test_analyze_replay(
    replay_file, instructions, convo, critic: LmmCritic, sc2api_mock
):
    # arrange
    reader = ReplayReader()
    session = AISession()

    replay = reader.load_replay(replay_file)
    session.initiate_from_new_replay(replay)
    response = session.stream_thread()

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
