import time
from typing import Optional

import pytest
from pydantic import BaseModel

from tests.conftest import load_test_settings


class SC2ApiEmulatorData(BaseModel):
    state: str = "ingame"
    menu_state: str = "ScreenHome/ScreenHome"
    additional_menu_state: Optional[str] = None
    replay: bool = False
    players: list[dict] = []
    displaytime: int = 0
    autotime: bool = True
    set_at: int = int(time.time())


# uses SC2ApiEmulator docker image
@pytest.mark.parametrize("opponent", ["BarCode", "HobGoblin"])
def test_sc2client_get_opponent(opponent, sc2apiemulator):
    from lib.sc2client import Player, SC2Client, Screen

    runtime_settings = load_test_settings()

    # arrange
    sc2api_set: SC2ApiEmulatorData = SC2ApiEmulatorData(
        menu_state=Screen.multiplayer.value
    )

    sc2api_set.players.append(
        Player(
            id=0,
            name=runtime_settings.student.name,
            race="Terr",
            result="Undecided",
        ).model_dump()
    )
    sc2api_set.players.append(
        Player(id=1, name=opponent, race="Zerg", result="Undecided").model_dump()
    )

    response = sc2apiemulator(sc2api_set)

    client = SC2Client()

    # act
    opponent_, race = client.get_opponent()

    # assert
    assert opponent == opponent_
    assert race == "Zerg"
