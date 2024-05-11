import logging
import threading
from time import sleep, time

import requests
from blinker import signal
from pydantic_core import ValidationError
from requests.exceptions import ConnectionError

from config import config

from .types import GameInfo, Result, ScanResult

log = logging.getLogger(f"{config.name}.{__name__}")

race_map = {
    "Terr": "TERRAN",
    "Prot": "PROTOSS",
    "Zerg": "ZERG",
    "random": "RANDOM",
}


class SC2Client:
    def get_gameinfo(self) -> GameInfo:
        try:
            response = requests.get(config.sc2_client_url + "/game")
            if response.status_code == 200:
                try:
                    game = GameInfo.model_validate_json(response.text)
                    return game
                except ValidationError as e:
                    log.warn(f"Invalid game data: {e}")
        except ConnectionError as e:
            log.warn("Could not connect to SC2 game client, is it running?")
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

    def get_ongoing_gameinfo(self) -> GameInfo:
        gameinfo = self.get_gameinfo()
        if (
            gameinfo
            and gameinfo.displayTime > 0
            and gameinfo.players[0].result != Result.undecided
        ):
            return gameinfo
        return None


sc2client = SC2Client()


class ClientAPIScanner(threading.Thread):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        self.scan_client_api()

    def scan_client_api(self):
        log.debug("Starting game client scanner")
        loading_screen = signal("loading_screen")
        while True:
            if self.stopped():
                log.debug("Stopping game client scanner")
                break

            gameinfo = sc2client.get_ongoing_gameinfo()

            if self.is_live_game(gameinfo):
                opponent = sc2client.get_opponent_name(gameinfo)
                mapname = ""

                scanresult = ScanResult(mapname=mapname, opponent=opponent)

                loading_screen.send(self, scanresult=scanresult)
            sleep(1)

    def is_live_game(self, gameinfo):
        return (
            gameinfo
            and gameinfo.displayTime > 0
            and gameinfo.players[0].result == Result.undecided
            and not gameinfo.isReplay
        )


if __name__ == "__main__":
    print(GameInfo.model_json_schema())
