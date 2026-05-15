import logging
import threading
from time import sleep

from shared import signal_queue
from src.events import NewMatchEvent
from src.lib.sc2client import SC2Client, is_live_game
from src.runtime.settings import Config, load_current_settings

from log import DEFAULT_LOGGER_NAME
log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")


class ClientAPIListener(threading.Thread):
    last_gameinfo = None

    sc2client: SC2Client

    def __init__(self, *, settings: Config | None = None):
        super().__init__()
        self.settings = settings or load_current_settings()
        self._stop_event = threading.Event()

        self.sc2client = SC2Client(settings=self.settings)

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        self.scan_client_api()

    def scan_client_api(self):
        log.debug("Starting game client scanner")

        while True:
            if self.stopped():
                log.debug("Stopping game client scanner")
                break

            gameinfo = self.sc2client.get_ongoing_gameinfo()

            if is_live_game(gameinfo):
                if gameinfo == self.last_gameinfo:
                    # same ongoing game, just later in time
                    if (
                        self.last_gameinfo
                        and gameinfo.displayTime >= self.last_gameinfo.displayTime
                    ):
                        continue

                self.last_gameinfo = gameinfo
                opponent, race = self.sc2client.get_opponent(gameinfo)
                mapname = ""

                scanresult = NewMatchEvent(mapname=mapname, opponent=opponent)
                signal_queue.put(scanresult)

            sleep(1)
