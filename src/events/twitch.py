import asyncio
import logging
import threading

from twitchAPI.chat import Chat, ChatMessage, EventData
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.helper import first
from twitchAPI.oauth import UserAuthenticationStorageHelper, UserAuthenticator
from twitchAPI.object.eventsub import ChannelFollowEvent, ChannelRaidEvent
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope, ChatEvent

from config import config
from shared import signal_queue
from src.events import TwitchChatEvent, TwitchFollowEvent, TwitchRaidEvent

log = logging.getLogger(f"{config.name}.{__name__}")

USER_SCOPE = [
    AuthScope.CHAT_READ,
    AuthScope.CHAT_EDIT,
    AuthScope.MODERATOR_READ_FOLLOWERS,
]


class TwitchListener(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()
        self.chat.stop()
        self.eventsub.stop()
        self.twitch.close()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        if config.twitch_mocked:
            asyncio.run(self.twitch_async_mocked())
        else:
            asyncio.run(self.twitch_async())

    async def on_ready(self, ready_event: EventData):
        log.debug(f"Bot ready, joining {config.twitch_channel}")
        await ready_event.chat.join_room(config.twitch_channel)

    async def on_follow(self, follow_event: ChannelFollowEvent):
        log.debug(f"Followed by {follow_event.event.user_name}")

        result = TwitchFollowEvent(
            user=follow_event.event.user_name, event=follow_event.to_dict()
        )
        signal_queue.put(result)

    async def on_raid(self, raid_event: ChannelRaidEvent):
        log.debug(
            f"Raided by {raid_event.event.from_broadcaster_user_name} with {raid_event.event.viewers} viewers"
        )

        result = TwitchRaidEvent(
            user=raid_event.event.from_broadcaster_user_name,
            viewers=raid_event.event.viewers,
            event=raid_event.to_dict(),
        )
        signal_queue.put(result)

    async def on_message(self, msg: ChatMessage):
        log.debug(f"Message in {msg.room.name}, {msg.user.name}: {msg.text}")
        result = TwitchChatEvent(
            user=msg.user.name, channel=msg.room.name, message=msg.text
        )
        signal_queue.put(result)

    async def twitch_async(self):
        """Start the twitch listener.

        Join the streamer chat channel, and subscribe to raid and follow events.
        """
        self.twitch = await Twitch(config.twitch_client_id, config.twitch_client_secret)
        helper = UserAuthenticationStorageHelper(self.twitch, USER_SCOPE)
        await helper.bind()

        self.chat = await Chat(self.twitch)
        self.chat.register_event(ChatEvent.READY, self.on_ready)
        self.chat.register_event(ChatEvent.MESSAGE, self.on_message)
        self.chat.start()

        user = await first(self.twitch.get_users())
        self.eventsub = EventSubWebsocket(self.twitch)
        self.eventsub.start()

        await self.eventsub.listen_channel_follow_v2(user.id, user.id, self.on_follow)
        await self.eventsub.listen_channel_raid(
            self.on_raid, to_broadcaster_user_id=user.id
        )

    async def twitch_async_mocked(self):
        """Unfortunately the mocked API needs a separate implementation so we can't
        just mock the twitch service and test the production code."""
        log.info("Starting mocked twitch listener")
        mock_scope = [
            AuthScope.MODERATOR_READ_FOLLOWERS,
        ]
        self.twitch = await Twitch(
            config.twitch_client_id,
            config.twitch_client_secret,
            base_url="http://localhost:8080/mock/",
            auth_base_url="http://localhost:8080/auth/",
        )
        self.twitch.auto_refresh_auth = False
        auth = UserAuthenticator(
            self.twitch, mock_scope, auth_base_url="http://localhost:8080/auth/"
        )
        token = await auth.mock_authenticate(config.twitch_mocked_user_id)
        await self.twitch.set_user_authentication(token, mock_scope)
        user = await first(self.twitch.get_users())

        self.eventsub = EventSubWebsocket(
            self.twitch,
            connection_url="ws://127.0.0.1:8080/ws",
            subscription_url="http://127.0.0.1:8080/",
        )
        self.eventsub.start()

        sub1_id = await self.eventsub.listen_channel_follow_v2(
            broadcaster_user_id=user.id,
            moderator_user_id=user.id,
            callback=self.on_follow,
        )
        log.info(
            f"twitch event trigger channel.follow -t {user.id} -u {sub1_id}  -T websocket"
        )
        sub2_id = await self.eventsub.listen_channel_raid(
            self.on_raid, to_broadcaster_user_id=user.id
        )
        log.info(
            f"twitch event trigger channel.raid -t {user.id} -u {sub2_id} -T websocket"
        )
