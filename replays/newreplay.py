import glob
import logging
import os
import threading
from os.path import basename, join
from pathlib import Path
from time import sleep

from blinker import signal

from config import config
from obs_tools.playerinfo import save_player_info
from replays.db import replaydb
from replays.reader import ReplayReader

log = logging.getLogger(f"{config.name}.{__name__}")
log.setLevel(logging.INFO)

newreplay = signal("replay")

reader = ReplayReader()


def wait_for_delete(file_path: Path, timeout: int = 10) -> bool:
    for _ in range(timeout):
        try:
            os.remove(file_path)
            return True
        except:
            sleep(1)
    return False


class NewReplayScanner(threading.Thread):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.daemon = True
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        self.replay_scanner()

    def replay_scanner(self):
        log.debug("Starting replay scanner")
        list_of_files = glob.glob(join(config.replay_folder, "*.SC2Replay"))

        while True:
            if self.stopped():
                log.debug("Stopping replay scanner")
                break
            new_list_of_files = glob.glob(join(config.replay_folder, "*.SC2Replay"))
            new_list_of_files = [f for f in new_list_of_files if f not in list_of_files]
            for file_path in new_list_of_files:
                sleep(3)
                replay_raw = reader.load_replay_raw(file_path)
                if reader.apply_filters(replay_raw):
                    log.info(f"New replay {basename(file_path)}")
                    replay = reader.to_typed_replay(replay_raw)
                    result = replaydb.upsert(replay)
                    if not result.acknowledged:
                        log.error(f"Failed to save {replay}")
                    result, player_info = save_player_info(replay)
                    if not result.acknowledged:
                        log.error(f"Failed to save player info for {replay}")
                    newreplay.send(self, replay=replay)
                else:
                    if reader.is_instant_leave(replay_raw) or reader.has_afk_player(
                        replay_raw
                    ):
                        wait_for_delete(file_path)
                        log.info(f"Deleted {basename(file_path)}")
            list_of_files = new_list_of_files + list_of_files
            sleep(config.deamon_polling_rate)
