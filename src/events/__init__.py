from config import AudioMode, CoachEvent, config
from src.events.events import (
    CastReplayEvent,
    NewMatchEvent,
    NewReplayEvent,
    TwitchChatEvent,
    TwitchFollowEvent,
    TwitchRaidEvent,
    WakeEvent,
)

if config.obs_integration:
    from src.events.loading_screen import NewMatchListener as GameStartedListener
else:
    from src.events.clientapi import ClientAPIListener as GameStartedListener

if config.audiomode in [AudioMode.full, AudioMode.voice_in]:
    if config.wakeword.engine == "porcupine":
        from src.events.wake_porcupine import WakeWordListener as WakeListener
    else:
        from src.events.wake_oww import WakeWordListener as WakeListener
else:
    from src.events.wake_key import WakeKeyListener as WakeListener

if CoachEvent.twitch in config.coach_events:
    from src.events.twitch import TwitchListener

from src.events.newreplay import NewReplayListener

__all__ = [
    "GameStartedListener",
    "WakeListener",
    "TwitchListener",
    "NewReplayListener",
    "NewMatchEvent",
    "WakeEvent",
    "TwitchChatEvent",
    "TwitchFollowEvent",
    "TwitchRaidEvent",
    "NewReplayEvent",
    "CastReplayEvent",
]
