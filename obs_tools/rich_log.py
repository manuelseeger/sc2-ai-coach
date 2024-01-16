import logging
from rich import print
from logging import LogRecord, Filterer, NOTSET, _checkLevel, _addHandlerRef, Handler
from time import sleep
from rich.console import Console
from config import config

console = Console()

THINKING = "Thinking..."


class Emojis:
    debug: str = ":bug:"
    info: str = ":information_source:"
    warning: str = ":warning:"
    error: str = ":x:"
    critical: str = ":skull:"
    aicoach: str = ":alien_monster:"
    mic: str = ":microphone:"
    loading_screen: str = ":tv:"
    replay: str = ":videocassette:"


EMOJI_MAP = {
    "obs_tools.wake": Emojis.mic,
    "obs_tools.parse_map_loading_screen": Emojis.loading_screen,
    "replays": Emojis.replay,
}


emoji_map_sorted_by_specificity = sorted(
    EMOJI_MAP.keys(), key=lambda x: x.count("."), reverse=True
)


def get_emoji(name: str, funcName: str) -> str:
    input_string = f"{name}.{funcName}".replace(f"{config.name}.", "")
    for key in emoji_map_sorted_by_specificity:
        if input_string.startswith(key):
            return EMOJI_MAP[key]

    return Emojis.aicoach


class TwitchObsLogHandler(Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last = None

        self.thinking = None

    def emit(self, record: LogRecord) -> None:
        if record.levelno < logging.INFO:
            return

        if self._last == record.msg:
            return

        self._last = record.msg

        # emoji = EMOJI_MAP.get(record.funcName, Emojis.aicoach)
        emoji = get_emoji(record.name, record.funcName)

        if record.funcName == "wait_on_run":
            self.thinking = console.status(f"{emoji} Thinking...", spinner="dots2")
            self.thinking.start()
            return
        else:
            if self.thinking:
                self.thinking.stop()

        self.print(record.msg, emoji=emoji)

    def print(self, message, emoji=Emojis.aicoach):
        console.print(f"{emoji} {message}")


if __name__ == "__main__":
    log = logging.getLogger("twitch")
    log.setLevel(logging.DEBUG)
    log.addHandler(TwitchObsLogHandler())

    log.info("I am Thinking", THINKING)

    sleep(4)
    log.info("Stopped thinking")
