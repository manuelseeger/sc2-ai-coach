import threading
from typing import Dict
import logging
from config import config
from blinker import signal
import glob
from os.path import join, basename
import os
from time import sleep
from .replaydb import ReplayDB

log = logging.getLogger(f"{config.name}.{__name__}")
log.setLevel(logging.INFO)

newreplay = signal("replay")

db = ReplayDB()


class NewReplayScanner(threading.Thread):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.daemon = True

    def run(self):
        self.replay_scanner()

    def replay_scanner(self):
        log.debug("Starting replay scanner")
        list_of_files = glob.glob(join(config.replay_folder, "*.SC2Replay"))

        while True:
            new_list_of_files = glob.glob(join(config.replay_folder, "*.SC2Replay"))
            new_list_of_files = [f for f in new_list_of_files if f not in list_of_files]
            for file_path in new_list_of_files:
                sleep(3)
                replay_raw = db.load_replay_raw(file_path)
                if db.apply_filters(replay_raw):
                    log.info(f"New replay {basename(file_path)}")
                    db.upsert_replay(replay_raw)
                    replay = db.to_typed_replay(replay_raw)
                    newreplay.send(self, replay=replay)
                else:
                    if db.is_instant_leave(replay_raw):
                        os.remove(file_path)
                        log.info(f"Deleted {basename(file_path)}")
            list_of_files = new_list_of_files + list_of_files
            sleep(config.deamon_polling_rate)
