import pytest

from src.matchhistory import get_sc2pulse_match_history
from src.replaydb.types import ToonHandle


# Amygdala (38) TvZ smurf leaves TvT.SC2Replay
@pytest.mark.parametrize(
    ("replay_file", "toon_handle"),
    [("Amygdala (38) TvZ smurf leaves TvT.SC2Replay", "2-S2-1-8773156")],
    indirect=["replay_file"],
)
def test_detect_smurf(replay_file, toon_handle):
    match_history = get_sc2pulse_match_history(toon_handle)

    race_report = match_history.race_report

    assert race_report["instant_leave_rate"].max() > 0.25
    assert race_report["winrate"].max() > 0.8


# @only_in_debugging
@pytest.mark.parametrize(
    "toon_handle_str",
    ["1-S2-1-1515247", "2-S2-1-1248982", "2-S2-1-8773156"],
)
def test_get_match_history(toon_handle_str):
    toon_handle = ToonHandle(toon_handle_str)

    match_history = get_sc2pulse_match_history(toon_handle)

    assert len(match_history) > 0

    match_history.data.to_csv(
        f"logs/match_history_{toon_handle_str}.csv",
        index=False,
        encoding="utf-8",
    )
