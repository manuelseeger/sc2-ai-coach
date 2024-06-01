from enum import Enum
from typing import List

from pydantic import BaseModel


class ScanResult(BaseModel):
    mapname: str
    opponent: str


class WakeResult(BaseModel):
    awake: bool


class Race(str, Enum):
    terran = "Terr"
    protoss = "Prot"
    zerg = "Zerg"
    random = "random"


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
