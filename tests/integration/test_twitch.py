import sys

import pytest

if sys.gettrace() is None:
    pytest.skip("Skipping debug-only integration test.", allow_module_level=True)

from coach import AISession
from src.events import TwitchChatEvent


def test_twitch_chat():
    session = AISession()

    chat = [
        TwitchChatEvent(
            channel="zatic",
            message="When was the last game zatic played?",
            user="hobgoblin",
        ),
        TwitchChatEvent(
            channel="zatic",
            message="This is so cool",
            user="tuorello",
        ),
        TwitchChatEvent(
            channel="zatic",
            message="I love this",
            user="tuorello",
        ),
        TwitchChatEvent(
            channel="zatic",
            message="and what time was it?",
            user="hobgoblin",
        ),
    ]

    for r in chat:
        session.handle_twitch_chat(twitch_chat=r)
