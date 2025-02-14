import time
from typing import Optional

import pytest
from pydantic import BaseModel

from config import config
from src.lib.sc2client import Player, SC2Client, Screen


class SC2ApiEmulatorData(BaseModel):
    state: str = "ingame"
    menu_state: str = Screen.home.value
    additional_menu_state: Optional[str] = None
    replay: bool = False
    players: list[Player] = []
    displaytime: int = 0
    autotime: bool = True
    set_at: int = int(time.time())


# uses SC2ApiEmulator docker image
@pytest.mark.parametrize("opponent", ["BarCode", "HobGoblin"])
def test_sc2client_get_opponent(opponent, sc2apiemulator):
    # arrange
    sc2api_set: SC2ApiEmulatorData = SC2ApiEmulatorData()

    sc2api_set.menu_state = Screen.multiplayer.value

    sc2api_set.players.append(
        Player(id=0, name=config.student.name, race="Terr", result="Undecided")
    )
    sc2api_set.players.append(
        Player(id=1, name=opponent, race="Zerg", result="Undecided")
    )

    response = sc2apiemulator(sc2api_set)

    client = SC2Client()

    # act
    opponent_, race = client.get_opponent()

    # assert
    assert opponent == opponent_
    assert race == "Zerg"
