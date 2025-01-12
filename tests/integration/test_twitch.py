import queue
from os.path import join
from time import sleep

import pytest
from numpy import sign
from rich import print

from coach import AISession
from obs_tools.twitch import TwitchListener
from obs_tools.types import TwitchChatResult
from shared import signal_queue
from tests.conftest import only_in_debugging


@only_in_debugging
def test_twitch_chat():

    session = AISession()

    chat = [
        TwitchChatResult(
            channel="zatic",
            message="When was the last game zatic played?",
            user="hobgoblin",
        ),
        TwitchChatResult(
            channel="zatic",
            message="This is so cool",
            user="tuorello",
        ),
        TwitchChatResult(
            channel="zatic",
            message="I love this",
            user="tuorello",
        ),
        TwitchChatResult(
            channel="zatic",
            message="and what time was it?",
            user="hobgoblin",
        ),
    ]

    for r in chat:
        session.handle_twitch_chat(__file__, twitch_chat=r)
