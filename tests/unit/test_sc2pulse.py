import pytest

from src.lib.sc2client import Race
from src.lib.sc2pulse import SC2PulseLeagueBounds, SC2PulseRace, get_division_for_mmr


def test_convert_race():
    zerg1 = SC2PulseRace.zerg
    zerg2 = Race.zerg

    assert zerg1 != zerg2

    protoss = Race.protoss

    assert protoss.value == "Prot"

    protoss = protoss.convert(SC2PulseRace)

    assert protoss.value == "PROTOSS"


@pytest.mark.parametrize(
    ("mmr", "expected_division"),
    [
        (1520, ("Bronze", "1")),
        (1300, ("Bronze", "2")),
        (1270, ("Bronze", "3")),
        (2133, ("Silver", "1")),
        (2000, ("Silver", "2")),
        (1900, ("Silver", "3")),
        (2600, ("Gold", "1")),
        (2500, ("Gold", "2")),
        (2400, ("Gold", "3")),
        (3000, ("Platinum", "1")),
        (2900, ("Platinum", "2")),
        (2800, ("Platinum", "3")),
        (4000, ("Diamond", "1")),
        (3800, ("Diamond", "2")),
        (3200, ("Diamond", "3")),
        (4800, ("Master", "1")),
        (4700, ("Master", "2")),
        (4500, ("Master", "3")),
        (5100, ("Grandmaster", "")),
    ],
)
def test_get_division_for_mmr(mmr, expected_division):
    division_data = {
        "EU": {
            "0": {"0": [1520, 1760], "1": [1279, 1520], "2": [1039, 1279]},
            "1": {"0": [2133, 2320], "1": [1947, 2133], "2": [1760, 1947]},
            "2": {"0": [2587, 2720], "1": [2453, 2587], "2": [2320, 2453]},
            "3": {"0": [2987, 3120], "1": [2853, 2987], "2": [2720, 2853]},
            "4": {"0": [3893, 4280], "1": [3507, 3893], "2": [3120, 3507]},
            "5": {"0": [4761, 5001], "1": [4520, 4761], "2": [4280, 4520]},
            "6": {"0": [0, 0], "1": [0, 0], "2": [0, 0]},
        }
    }

    division = get_division_for_mmr(
        mmr=mmr,
        league_bounds=SC2PulseLeagueBounds(region="EU", bounds=division_data["EU"]),
    )
    assert division == expected_division
