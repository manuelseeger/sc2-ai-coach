import requests
from pydantic import BaseModel
from typing import List
from enum import Enum
from pydantic_core import ValidationError
from time import time, sleep
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

    def get_opponent_name(self, gameinfo=None) -> str:
        if gameinfo is None:
            gameinfo = self.get_gameinfo()
        if gameinfo:
            for player in gameinfo.players:
                if player.name != config.student.name:
                    return player.name
        return None

    def wait_for_gameinfo(self, timeout: int = 20, delay: float = 0.5) -> GameInfo:
        start_time = time()
        while time() - start_time < timeout:
            gameinfo = self.get_gameinfo()
            if gameinfo and gameinfo.displayTime > 0:
                return gameinfo
            sleep(delay)
        return None


sc2client = SC2Client()
