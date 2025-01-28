from config import AudioMode, config

if config.obs_integration:
    from .events.parse_map_loading_screen import (
        LoadingScreenScanner as GameStartedScanner,
    )
else:
    from .events.clientapi import ClientAPIScanner as GameStartedScanner


if config.audiomode in [AudioMode.full, AudioMode.voice_in]:
    from .events.wakeword import WakeWordListener as WakeListener
else:
    from .events.wakekey import WakeKeyListener as WakeListener
