from config import AudioMode, config

if config.obs_integration:
    from .parse_map_loading_screen import LoadingScreenScanner as GameStartedScanner
else:
    from .sc2client import ClientAPIScanner as GameStartedScanner


if config.audiomode in [AudioMode.full, AudioMode.voice_in]:
    from .wakeword import WakeWordListener as WakeListener
else:
    from .wakekey import WakeKeyListener as WakeListener
