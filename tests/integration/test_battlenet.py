import pytest
from rich import print

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
