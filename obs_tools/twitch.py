import asyncio
import logging
import threading

from twitchAPI.chat import Chat, ChatCommand, ChatMessage, ChatSub, EventData
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope, ChatEvent

from config import config
from shared import signal_queue

from .types import TwitchResult

log = logging.getLogger(f"{config.name}.{__name__}")

USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]


class TwitchListener(threading.Thread):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.daemon = True
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()
        self.chat.stop()
        self.twitch.close()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        asyncio.run(self.twitch_async())

    async def on_ready(self, ready_event: EventData):
        log.debug(f"Bot ready, joining {config.twitch_channel}")
        await ready_event.chat.join_room(config.twitch_channel)

    async def on_message(self, msg: ChatMessage):
        log.debug(f"Message in {msg.room.name}, {msg.user.name}: {msg.text}")
        result = TwitchResult(
            user=msg.user.name, channel=msg.room.name, message=msg.text
        )
        await signal_queue.put(result)

    async def twitch_async(self):

        self.twitch = await Twitch(config.twitch_client_id, config.twitch_client_secret)
        auth = UserAuthenticator(self.twitch, USER_SCOPE)
        token, refresh_token = await auth.authenticate()
        await self.twitch.set_user_authentication(token, USER_SCOPE, refresh_token)

        self.chat = await Chat(self.twitch)
        self.chat.register_event(ChatEvent.READY, self.on_ready)
        self.chat.register_event(ChatEvent.MESSAGE, self.on_message)
        self.chat.start()
