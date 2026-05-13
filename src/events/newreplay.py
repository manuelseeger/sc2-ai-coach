import logging
import os
from os.path import basename
from pathlib import Path
from time import sleep
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import config
from shared import signal_queue
from src.events import NewReplayEvent
from src.persistence.replay_store import ReplayStore, get_replay_store
from src.playerinfo import save_player_info
from src.replays.reader import ReplayReader
from src.util import wait_for_file

log = logging.getLogger(f"{config.name}.{__name__}")
log.setLevel(logging.INFO)


reader = ReplayReader()


def wait_for_delete(file_path: Path, timeout: int = 10) -> bool:
    for _ in range(timeout):
        try:
            os.remove(file_path)
            return True
        except:  # noqa: E722
            sleep(1)
    return False


class NewReplayHandler(FileSystemEventHandler):
    def __init__(
        self,
        *,
        replay_store: ReplayStore | None = None,
        save_player_info_fn: Callable = save_player_info,
    ):
        super().__init__()
        self.replay_store = replay_store or get_replay_store()
        self.save_player_info = save_player_info_fn

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
            result = self.replay_store.upsert(replay)
            if not result.acknowledged:
                log.error(f"Failed to save {replay}")
            result, player_info = self.save_player_info(replay)
            if not result.acknowledged:
                log.error(f"Failed to save player info for {replay}")

            signal_queue.put(NewReplayEvent(replay=replay))
        else:
            if reader.is_instant_leave(replay_raw) or reader.has_afk_player(replay_raw):
                wait_for_delete(file_path)
                log.info(f"Deleted {basename(file_path)}")


class NewReplayListener(Observer):
    def __init__(
        self,
        *,
        replay_store: ReplayStore | None = None,
        save_player_info_fn: Callable = save_player_info,
    ):
        super().__init__()
        self.event_handler = NewReplayHandler(
            replay_store=replay_store,
            save_player_info_fn=save_player_info_fn,
        )
        self.schedule(self.event_handler, path=config.replay_folder, recursive=False)
