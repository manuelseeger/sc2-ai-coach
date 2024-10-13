from os.path import join

import pytest
from rich import print

from coach import AISession
from obs_tools.types import TwitchResult
from replays.reader import ReplayReader


def test_twitch_chat():

    session = AISession()

    chat = [
        TwitchResult(
            channel="zatic",
            message="When was the last game zatic played?",
            user="hobgoblin",
        ),
        TwitchResult(
            channel="zatic",
            message="This is so cool",
            user="tuorello",
        ),
        TwitchResult(
            channel="zatic",
            message="I love this",
            user="tuorello",
        ),
        TwitchResult(
            channel="zatic",
            message="and what time was it?",
            user="hobgoblin",
        ),
    ]

    for r in chat:
        session.handle_twitch_chat(__file__, twitch_chat=r)
