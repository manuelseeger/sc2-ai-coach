import threading
from blinker import signal
import keyboard
import logging
from config import config
from .types import WakeResult

log = logging.getLogger(f"{config.name}.{__name__}")

wakeup = signal("wakeup")


class WakeKeyListener(threading.Thread):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.daemon = True

    def run(self):
        keyboard.add_hotkey(config.wake_key, self.listen_for_wake_key)

    def listen_for_wake_key(self):
        log.debug("Wake key pressed")
        wakeup.send(self, wakeresult=WakeResult(awake=True))