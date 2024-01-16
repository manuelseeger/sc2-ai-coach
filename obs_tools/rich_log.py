import logging
from rich import print
from logging import LogRecord, Filterer, NOTSET, _checkLevel, _addHandlerRef, Handler
from time import sleep
from rich.console import Console
from rich.status import Status
from config import config
from typing import Dict

console = Console()


thinking_status = console.status("Thinking...", spinner="dots2")
transcribing_status = console.status("Transcribing...", spinner="point")

STATUS_METHODS: Dict[str, Status] = {
    "wait_on_run": thinking_status,
    "transcribe": transcribing_status,
}


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
    transcribe: str = ":keyboard:"


EMOJI_MAP = {
    "obs_tools.wake": Emojis.mic,
    "obs_tools.parse_map_loading_screen": Emojis.loading_screen,
    "replays": Emojis.replay,
    "obs_tools.mic": Emojis.mic,
    "aicoach.transcribe": Emojis.transcribe,
    "converse": Emojis.mic,
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

        self.fqn = None

    def emit(self, record: LogRecord) -> None:
        if record.levelno < logging.INFO:
            return

        if self._last == record.msg:
            return

        self._last = record.msg

        emoji = get_emoji(record.name, record.funcName)

        if self.is_status(record):
            self.set_status(record)
            self.fqn = self.get_fqn(record.name, record.funcName)
            return

        msg = ""
        if record.levelno == logging.WARN:
            msg = f":warning: [yellow]{record.msg}[/yellow]"
        elif record.levelno == logging.ERROR:
            msg = f":bomb: [red]{record.msg}[/red]"
        else:
            msg = record.msg

        self.print(msg, emoji=emoji)
        self.fqn = self.get_fqn(record.name, record.funcName)

    def get_fqn(self, name: str, funcName: str):
        return f"{name}.{funcName}"

    def print(self, message, emoji=Emojis.aicoach):
        console.print(f"{emoji} {message}")

    def set_status(self, record: LogRecord) -> None:
        self.stop_statuses()
        if self.fqn != self.get_fqn(record.name, record.funcName):
            STATUS_METHODS[record.funcName].start()

    def stop_statuses(self):
        for status in STATUS_METHODS.values():
            status.stop()

    def get_status(self, record: LogRecord) -> Status:
        if record.funcName in STATUS_METHODS.keys():
            return STATUS_METHODS[record.funcName]
        return None

    def is_status(self, record: LogRecord) -> bool:
        if record.funcName in STATUS_METHODS.keys():
            return True
        return False


if __name__ == "__main__":
    log = logging.getLogger("twitch")
    log.setLevel(logging.DEBUG)
    log.addHandler(TwitchObsLogHandler())

    log.info("I am Thinking")

    sleep(4)
    log.info("Stopped thinking")
