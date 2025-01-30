import queue
from time import sleep

import pytest
from rich import print

from config import config
from shared import signal_queue
from src.events.twitch import TwitchListener


@pytest.mark.skipif(
    config.twitch_mocked is False,
    reason="Only run when twitch events are mocked locally.",
)
def test_channel_follow():

    twitch = TwitchListener(name="twitch")
    twitch.start()

    while not twitch.stopped():
        try:
            result = signal_queue.get()
            print(result)
            signal_queue.task_done()
        except queue.Empty:
            pass
        finally:
            sleep(1)
