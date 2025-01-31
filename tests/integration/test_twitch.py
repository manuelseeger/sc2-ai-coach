from coach import AISession
from src.events import TwitchChatEvent
from tests.conftest import only_in_debugging


@only_in_debugging
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
        session.handle_twitch_chat(__file__, twitch_chat=r)
