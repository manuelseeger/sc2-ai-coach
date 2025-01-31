from src.events.events import *
from config import AudioMode, config

if config.obs_integration:
    from src.events.loading_screen import (
        NewMatchListener as GameStartedListener,
    )
else:
    from src.events.clientapi import ClientAPIListener as GameStartedListener

if config.audiomode in [AudioMode.full, AudioMode.voice_in]:
    from src.events.wakeword import WakeWordListener as WakeListener
else:
    from src.events.wakekey import WakeKeyListener as WakeListener

from src.events.twitch import TwitchListener
from src.events.newreplay import NewReplayListener
