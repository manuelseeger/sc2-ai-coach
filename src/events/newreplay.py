import logging
import os
from os.path import basename
from pathlib import Path
from time import sleep

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from shared import signal_queue
from src.events import NewReplayEvent
from src.persistence.replay_store import ReplayStore, get_replay_store
from src.playeridentity import PlayerIdentityEnricher, PlayerIdentityEnrichmentError
from src.replays.reader import ReplayReader
from src.runtime.settings import Config, load_current_settings
from src.util import wait_for_file

from log import DEFAULT_LOGGER_NAME
log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")
log.setLevel(logging.INFO)


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
        player_identity_enricher: PlayerIdentityEnricher | None = None,
        settings: Config | None = None,
    ):
        super().__init__()
        self.settings = settings or load_current_settings()
        self.replay_store = replay_store or get_replay_store()
        if player_identity_enricher is None:
            raise ValueError("player_identity_enricher must be provided")
        self.player_identity_enricher = player_identity_enricher
        self.reader = ReplayReader(settings=self.settings)

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".SC2Replay"):
            if wait_for_file(event.src_path):
                self.process_new_file(event.src_path)

    def process_new_file(self, file_path: str):
        replay_raw = self.reader.load_replay_raw(file_path)
        if self.reader.apply_filters(replay_raw):
            log.info(f"New replay {basename(file_path)}")
            replay = self.reader.to_typed_replay(replay_raw)
            result = self.replay_store.upsert(replay)
            if not result.acknowledged:
                log.error(f"Failed to save {replay}")
            try:
                self.player_identity_enricher.save_from_replay(replay)
            except PlayerIdentityEnrichmentError as exc:
                log.error(f"Failed to enrich player identity: {exc}")

            signal_queue.put(NewReplayEvent(replay=replay))
        else:
            if self.reader.is_instant_leave(replay_raw) or self.reader.has_afk_player(
                replay_raw
            ):
                wait_for_delete(file_path)
                log.info(f"Deleted {basename(file_path)}")


class NewReplayListener(Observer):
    def __init__(
        self,
        *,
        replay_store: ReplayStore | None = None,
        player_identity_enricher: PlayerIdentityEnricher | None = None,
        settings: Config | None = None,
    ):
        super().__init__()
        self.settings = settings or load_current_settings()
        if player_identity_enricher is None:
            raise ValueError("player_identity_enricher must be provided")
        self.event_handler = NewReplayHandler(
            replay_store=replay_store,
            player_identity_enricher=player_identity_enricher,
            settings=self.settings,
        )
        self.schedule(
            self.event_handler,
            path=self.settings.replay_folder,
            recursive=False,
        )
