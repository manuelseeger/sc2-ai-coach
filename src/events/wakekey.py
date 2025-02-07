import logging
import threading

import keyboard

from config import config
from src.events.types import WakeResult

log = logging.getLogger(f"{config.name}.{__name__}")

from shared import signal_queue


class WakeKeyListener(threading.Thread):
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
        keyboard.add_hotkey(config.wake_key, self.listen_for_wake_key)
        self._stop_event.wait()

    def listen_for_wake_key(self):
        log.debug("Wake key pressed")
        signal_queue.put(WakeResult(awake=True))
