import logging
import threading

import keyboard

from shared import signal_queue
from events import WakeEvent
from runtime.settings import Config, get_config

from log import DEFAULT_LOGGER_NAME

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")


class WakeKeyListener(threading.Thread):
    def __init__(self, *, settings: Config | None = None):
        super().__init__()
        self.settings = settings or get_config()
        self.daemon = True
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        keyboard.add_hotkey(self.settings.wake_key, self.listen_for_wake_key)
        self._stop_event.wait()

    def listen_for_wake_key(self):
        log.debug("Wake key pressed")
        signal_queue.put(WakeEvent(awake=True))
