import logging
import os
from os.path import basename
from pathlib import Path
from time import sleep

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import config
from shared import signal_queue
from src.events.types import NewReplayResult
from src.playerinfo import save_player_info
from src.replaydb.db import replaydb
from src.replaydb.reader import ReplayReader
from src.replaydb.util import wait_for_file

log = logging.getLogger(f"{config.name}.{__name__}")
log.setLevel(logging.INFO)


reader = ReplayReader()


def wait_for_delete(file_path: Path, timeout: int = 10) -> bool:
    for _ in range(timeout):
        try:
            os.remove(file_path)
            return True
        except:
            sleep(1)
    return False


class NewReplayHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".SC2Replay"):
            if wait_for_file(event.src_path):
                self.process_new_file(event.src_path)

    def process_new_file(self, file_path: str):

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

            signal_queue.put(NewReplayResult(replay=replay))
        else:
            if reader.is_instant_leave(replay_raw) or reader.has_afk_player(replay_raw):
                wait_for_delete(file_path)
                log.info(f"Deleted {basename(file_path)}")


class NewReplayScanner(Observer):
    def __init__(self):
        super().__init__()
        self.event_handler = NewReplayHandler()
        self.schedule(self.event_handler, path=config.replay_folder, recursive=False)
