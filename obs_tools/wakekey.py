import logging
import threading

import keyboard
from blinker import signal

from config import config

from .types import WakeResult

log = logging.getLogger(f"{config.name}.{__name__}")

wakeup = signal("wakeup")


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
        wakeup.send(self, wakeresult=WakeResult(awake=True))
