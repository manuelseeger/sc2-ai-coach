# pyright: reportOperatorIssue=none
import pandas as pd
import pytest

from src.matchhistory import MatchHistory


@pytest.mark.parametrize(
    "resource_file",
    [
        "match_history_barcode_smurf_2-S2-1-8773156.csv",
    ],
    indirect=True,
)
def test_build_race_report(resource_file):
    df = pd.read_csv(resource_file)
    match_history = MatchHistory(data=df)

    race_report = match_history.race_report

    assert race_report.loc["TvZ", "winrate"] > 0.9
    assert race_report.loc["TvP", "instant_leave_rate"] > 0.15
    assert race_report.loc["TvT", "instant_leave_rate"] > 0.15
