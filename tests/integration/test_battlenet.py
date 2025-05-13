import datetime

import pytest
from rich import print

from config import config
from src.lib.battlenet import BattleNet
from src.lib.sc2pulse import SC2PulseClient, SC2PulseRace


def test_get_barcode_character_ids():
    barcode = "IIIIIIIIIIII"

    sc2pulse = SC2PulseClient()

    chars = sc2pulse.character_search_advanced(name=barcode)

    print(len(chars))
    assert len(chars) > 0


def test_get_unmasked_player():
    barcode = "IIIIIIIIIIII"

    sc2pulse = SC2PulseClient()

    players = sc2pulse.get_unmasked_players(
        opponent=barcode, race=SC2PulseRace.zerg.value, mmr=4000
    )

    print(players)


@pytest.mark.parametrize(
    ("profile_id", "expected_name"),
    [
        (2372922, "jay"),
        (691545, "zatic"),
    ],
)
def test_get_profile(profile_id, expected_name):
    bnet = BattleNet()
    profile = bnet.get_profile(profile_id)

    print(profile)

    assert profile is not None
    assert profile.summary.displayName == expected_name


def test_get_current_season():
    sc2pulse = SC2PulseClient()
    season = sc2pulse.get_current_season()
    assert season.battlenetId == config.season
    assert season.end > datetime.datetime.now()


def test_get_season_bounds():
    sc2pulse = SC2PulseClient()
    season = sc2pulse.get_current_season()
    bounds = sc2pulse.get_league_bounds(season.battlenetId)

    assert bounds.bronze[0][1] < 2000
    assert bounds is not None


def get_division_for_mmr():
    sc2pulse = SC2PulseClient()
    season = sc2pulse.get_current_season()
    bounds = sc2pulse.get_league_bounds(season.battlenetId)

    mmr = 2000
    division = sc2pulse.get_division_for_mmr(mmr, bounds)
    assert division is not None
    assert division.league == "Bronze"
    assert division.division == 1
