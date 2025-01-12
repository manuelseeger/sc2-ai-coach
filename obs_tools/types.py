from email import message
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from replays.util import convert_enum


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


class ScanResult(BaseModel):
    mapname: str
    opponent: str


class WakeResult(BaseModel):
    awake: bool


class TwitchResult(BaseModel):
    channel: Optional[str] = None
    event: Optional[dict] = None


class TwitchChatResult(TwitchResult):
    user: str
    message: str


class TwitchFollowResult(TwitchResult):
    user: str


class TwitchRaidResult(TwitchResult):
    user: str
    viewers: int


class Race(str, Enum):
    terran = "Terr"
    protoss = "Prot"
    zerg = "Zerg"
    random = "random"

    normal_map = {
        "Terr": "Terran",
        "Prot": "Protoss",
        "Zerg": "Zerg",
        "random": "Random",
    }

    def normalize(self):
        return self.normal_map[self.value]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.value == other or self.normalize() == other
        else:
            return self == other

    def convert(self, other: Enum):
        return convert_enum(self, other)


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
