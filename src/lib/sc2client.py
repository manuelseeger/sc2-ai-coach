import logging
from enum import Enum
from time import sleep, time
from typing import List
from urllib.parse import urljoin

import httpx
from httpx import ConnectError
from pydantic import BaseModel
from pydantic_core import ValidationError

from config import config

log = logging.getLogger(f"{config.name}.{__name__}")


class Screen(str, Enum):
    loading = "ScreenLoading/ScreenLoading"
    score = "ScreenScore/ScreenScore"
    home = "ScreenHome/ScreenHome"
    background = "ScreenBackgroundSC2/ScreenBackgroundSC2"
    foreground = "ScreenForegroundSC2/ScreenForegroundSC2"
    navigation = "ScreenNavigationSC2/ScreenNavigationSC2"
    userprofile = "ScreenUserProfile/ScreenUserProfile"
    multiplayer = "ScreenMultiplayer/ScreenMultiplayer"
    single = "ScreenSingle/ScreenSingle"
    collection = "ScreenCollection/ScreenCollection"
    coopcampaign = "ScreenCoopCampaign/ScreenCoopCampaign"
    custom = "ScreenCustom/ScreenCustom"
    replay = "ScreenReplay/ScreenReplay"
    battlelobby = "ScreenBattleLobby/ScreenBattleLobby"


class Race(str, Enum):
    terran = "Terr"
    protoss = "Prot"
    zerg = "Zerg"
    random = "random"

    normal_map: dict = {
        "Terr": "Terran",
        "Prot": "Protoss",
        "Zerg": "Zerg",
        "random": "Random",
    }

    def normalize(self):
        return self.normal_map.get(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.value == other or self.normalize() == other
        else:
            return self == other

    def convert(self, other: Enum):
        return other[self.name]


class Result(str, Enum):
    win = "Victory"
    loss = "Defeat"
    undecided = "Undecided"
    tie = "Tie"


class Player(BaseModel):
    id: int
    name: str
    type: str
    race: Race
    result: Result


class GameInfo(BaseModel):
    """
    {
        isReplay: false,
        displayTime: 93,
        players: [
            {
                id: 1,
                name: "Owlrazum",
                type: "user",
                race: "Terr",
                result: "Undecided"
            },
            {
                id: 2,
                name: "zatic",
                type: "user",
                race: "Zerg",
                result: "Undecided"
            }
        ]
    }
    """

    isReplay: bool
    displayTime: float
    players: List[Player]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GameInfo):
            return (
                self.isReplay == other.isReplay
                and len(self.players) == len(other.players)
                and all(
                    self_player == other_player
                    for self_player, other_player in zip(self.players, other.players)
                )
            )
        else:
            return False

    def is_decided(self) -> bool:
        return (
            self.displayTime > 0
            and len(self.players) > 0
            and all(player.result != Result.undecided for player in self.players)
        )


class UIInfo(BaseModel):
    activeScreens: set[Screen]


class SC2Client:

    http_client: httpx.Client

    def __init__(self, http_client: httpx.Client = None):
        if http_client:
            self.http_client = http_client
        else:
            self.http_client = httpx.Client()

    def get_gameinfo(self) -> GameInfo:
        try:
            game = self._get_info("/game")
            gameinfo = GameInfo.model_validate_json(game)
            return gameinfo
        except ValidationError as e:
            log.warning(f"Invalid game data: {e}")
        return None

    def get_uiinfo(self) -> UIInfo:
        try:
            ui = self._get_info("/ui")
            uiinfo = UIInfo.model_validate_json(ui)
            return uiinfo
        except ValidationError as e:
            log.warning(f"Invalid UI data: {e}")
        return None

    def get_opponent(self, gameinfo=None) -> tuple[str, Race]:
        if gameinfo is None:
            gameinfo = self.get_gameinfo()
        if gameinfo:
            for player in gameinfo.players:
                if player.name != config.student.name:
                    return player.name, player.race
        return (None, None)

    def _get_info(self, path) -> str:
        try:
            response = self.http_client.get(urljoin(config.sc2_client_url, path))
            if response.status_code == 200:
                return response.text
        except ConnectError as e:
            log.warning("Could not connect to SC2 game client, is SC2 running?")
        return None

    def wait_for_gameinfo(
        self, timeout: int = 20, delay: float = 0.5, ongoing=False
    ) -> GameInfo:
        start_time = time()
        while time() - start_time < timeout:
            if ongoing:
                gameinfo = self.get_ongoing_gameinfo()
            else:
                gameinfo = self.get_gameinfo()
            if gameinfo and gameinfo.displayTime > 0:
                return gameinfo
            sleep(delay)
        return None

    def get_ongoing_gameinfo(self) -> GameInfo:
        gameinfo = self.get_gameinfo()
        if (
            gameinfo
            and gameinfo.displayTime > 0
            and len(gameinfo.players) > 0
            and gameinfo.players[0].result == Result.undecided
        ):
            return gameinfo
        return None


def is_live_game(gameinfo: GameInfo) -> bool:
    return (
        gameinfo
        and gameinfo.displayTime > 0
        and gameinfo.players[0].result == Result.undecided
        and not gameinfo.isReplay
    )


if __name__ == "__main__":
    print(GameInfo.model_json_schema())
