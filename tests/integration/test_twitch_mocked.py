import queue
from time import sleep

import pytest
from rich import print

from obs_tools.twitch import TwitchListener
from shared import signal_queue


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
