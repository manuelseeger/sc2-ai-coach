import logging
import threading
from time import sleep, time
from urllib.parse import urljoin

import requests
from blinker import signal
from pydantic_core import ValidationError
from requests.exceptions import ConnectionError

from config import config

from .types import GameInfo, Race, Result, ScanResult, Screen, UIInfo

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
            game = self._get_info("/game")
            gameinfo = GameInfo.model_validate_json(game)
            return gameinfo
        except ValidationError as e:
            log.warn(f"Invalid game data: {e}")
        return None

    def get_uiinfo(self) -> UIInfo:
        try:
            ui = self._get_info("/ui")
            uiinfo = UIInfo.model_validate_json(ui)
            return uiinfo
        except ValidationError as e:
            log.warn(f"Invalid UI data: {e}")
        return None

    def get_opponent(self, gameinfo=None) -> tuple[str,Race]:
        if gameinfo is None:
            gameinfo = self.get_gameinfo()
        if gameinfo:
            for player in gameinfo.players:
                if player.name != config.student.name:
                    return player.name, player.race
        return (None, None)

    def _get_info(self, path) -> str:
        try:
            response = requests.get(urljoin(config.sc2_client_url, path))
            if response.status_code == 200:
                return response.text
        except ConnectionError as e:
            log.warn("Could not connect to SC2 game client, is SC2 running?")
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


sc2client = SC2Client()


class ClientAPIScanner(threading.Thread):

    last_gameinfo = None

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

            if is_live_game(gameinfo):
                if gameinfo == self.last_gameinfo:
                    # same ongoing game, just later in time
                    if gameinfo.displayTime >= self.last_gameinfo.displayTime:
                        continue

                self.last_gameinfo = gameinfo
                opponent, race = sc2client.get_opponent(gameinfo)
                mapname = ""

                scanresult = ScanResult(mapname=mapname, opponent=opponent)

                loading_screen.send(self, scanresult=scanresult)
            sleep(1)


def is_live_game(gameinfo: GameInfo) -> bool:
    return (
        gameinfo
        and gameinfo.displayTime > 0
        and gameinfo.players[0].result == Result.undecided
        and not gameinfo.isReplay
    )


if __name__ == "__main__":
    print(GameInfo.model_json_schema())
