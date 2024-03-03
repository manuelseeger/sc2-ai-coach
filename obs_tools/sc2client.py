import requests
from pydantic import BaseModel
from typing import List
from enum import Enum
from pydantic_core import ValidationError
import logging
from config import config

log = logging.getLogger(f"{config.name}.{__name__}")

race_map = {
    "Terr": "TERRAN",
    "Prot": "PROTOSS",
    "Zerg": "ZERG",
    "random": "RANDOM",
}


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
    isReplay: bool
    displayTime: float
    players: List[Player]


class SC2Client:

    def get_gameinfo(self) -> GameInfo:
        response = requests.get("http://127.0.0.1:6119/game")
        if response.status_code == 200:
            try:
                game = GameInfo.model_validate_json(response.text)
                return game
            except ValidationError as e:
                log.warn(f"Invalid game data: {e}")
        return None

    def get_opponent_name(self) -> str:
        game = self.get_gameinfo()
        if game:
            for player in game.players:
                if player.name != config.student.name:
                    return player.name
        return None
