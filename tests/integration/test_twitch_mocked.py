import queue
from time import sleep

import pytest
from rich import print

pytest.importorskip("twitchAPI")

from shared import signal_queue
from tests.conftest import load_test_settings


def test_channel_follow():
    runtime_settings = load_test_settings()

    if runtime_settings.twitch_mocked is False:
        pytest.skip("Only run when twitch events are mocked locally.")

    from src.events.twitch import TwitchListener

    twitch = TwitchListener(name="twitch")
    twitch.start()

    while not twitch.stopped():
        try:
            result = signal_queue.get_nowait()
            print(result)
            signal_queue.task_done()
        except queue.Empty:
            pass
        finally:
            sleep(1)
