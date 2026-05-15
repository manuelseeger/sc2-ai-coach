import sys

import pandas as pd
import parametrize_from_file
import pytest

if sys.gettrace() is None:
    pytest.skip("Skipping debug-only LLM test.", allow_module_level=True)

from coach import AISession
from src.matchhistory import MatchHistory
from src.persistence.replay_store import PlayerInfo
from tests.critic import LmmCritic
from tests.mocks import MicMock, TranscriberMock, TTSMock


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
    mocker.patch.object(
        session.player_resolver,
        "resolve_player",
        return_value=playerinfo,
    )
    mocker.patch.object(
        session.replay_store, "get_recent_for_player", return_value=past_replays
    )
    mocker.patch("src.session.get_sc2pulse_match_history", return_value=match_history)

    # act
    session.initiate_from_game_start(mapname, opponent, mmr)
    response = session.stream_conversation()

    # assert
    critic_init = "You are given responses about a player's match history. Determine whether the response satisfies the evaluation criteria.\n\n"
    critic_init += "EVALUATION CRITERIA: " + criteria

    critique = critic.evaluate_one_shot(critic_init, response)

    print(critique.justification)
    assert critique.passed
