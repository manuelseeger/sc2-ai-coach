import pytest

from obs_tools.smurfs import get_sc2pulse_match_history
from tests.conftest import only_in_debugging


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


@only_in_debugging
@pytest.mark.parametrize(
    "toon_handle",
    ["2-S2-1-1248982", "2-S2-1-8773156"],
)
def test_get_match_history(toon_handle):
    match_history = get_sc2pulse_match_history(toon_handle)

    assert len(match_history) > 0

    match_history.data.to_csv(
        f"logs/match_history_{toon_handle}.csv",
        index=False,
        encoding="utf-8",
    )
