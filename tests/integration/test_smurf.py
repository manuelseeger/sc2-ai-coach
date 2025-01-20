import pytest
from rich import print

from obs_tools.smurfs import build_race_report, get_sc2pulse_match_history


# Amygdala (38) TvZ smurf leaves TvT.SC2Replay
@pytest.mark.parametrize(
    ("replay_file", "toon_handle"),
    [("Amygdala (38) TvZ smurf leaves TvT.SC2Replay", "2-S2-1-8773156")],
    indirect=["replay_file"],
)
def test_detect_smurf(replay_file, toon_handle):

    match_history = get_sc2pulse_match_history(toon_handle)

    race_report = build_race_report(match_history)

    assert race_report["instant_leave_rate"].max() > 0.2
    assert race_report["winrate"].max() > 0.8
