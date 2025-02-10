from src.lib.sc2client import SC2Client
from src.replaydb.util import is_barcode
from tests.conftest import only_in_debugging

from config import config
import pytest


# SC2 must be running and a game must be in progress or have been played recently
# or use https://github.com/manuelseeger/sc2apiemulator
@pytest.mark.parametrize("opponent", ["BarCode", "HobGoblin"])
@only_in_debugging
def test_sc2client_get_opponent(opponent, sc2apiemulator, sc2api_set):
    # arrange

    sc2api_set["state"] = "ingame"
    sc2api_set["menu_state"] = "ScreenMultiplayer/ScreenMultiplayer"
    sc2api_set["enabled1"] = True
    sc2api_set["enabled2"] = True
    sc2api_set["name1"] = config.student.name
    sc2api_set["name2"] = opponent
    sc2api_set["race1"] = "Terr"
    sc2api_set["race2"] = "Zerg"

    response = sc2apiemulator(sc2api_set)

    client = SC2Client()

    # act
    opponent_, race = client.get_opponent()

    # assert
    assert opponent == opponent_
    assert race == "Zerg"
