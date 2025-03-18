import pandas as pd
import parametrize_from_file

from coach import AISession
from src.matchhistory import MatchHistory
from src.replaydb.types import PlayerInfo
from tests.conftest import only_in_debugging
from tests.critic import LmmCritic
from tests.mocks import MicMock, TranscriberMock, TTSMock


@only_in_debugging
@parametrize_from_file(indirect=["resource_file"])
def test_detects_smurfing(
    resource_file,
    mapname,
    opponent,
    mmr,
    criteria,
    mocker,
    critic: LmmCritic,
):
    # arrange
    session = AISession()

    toon_handle = "2-S2-1-8773156"
    playerinfo = PlayerInfo(id=toon_handle, name=opponent, toon_handle=toon_handle)
    past_replays = []

    df = pd.read_csv(resource_file)
    match_history = MatchHistory(data=df)

    mocker.patch("coach.mic", MicMock())
    mocker.patch("coach.tts", TTSMock())
    mocker.patch("coach.transcriber", TranscriberMock(data=[]))
    mocker.patch(
        "coach.resolve_replays_from_current_opponent",
        return_value=(playerinfo, past_replays),
    )
    mocker.patch("coach.get_sc2pulse_match_history", return_value=match_history)

    # act
    session.initiate_from_game_start(mapname, opponent, mmr)
    response = session.stream_thread()

    # assert
    critic_init = "You are given responses about a player's match history. Determine whether the response satisfies the evaluation criteria.\n\n"
    critic_init += "EVALUATION CRITERIA: " + criteria

    critique = critic.evaluate_one_shot(critic_init, response)

    print(critique.justification)
    assert critique.passed
