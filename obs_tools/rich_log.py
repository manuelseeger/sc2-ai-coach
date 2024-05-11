import logging
from logging import Handler, LogRecord
from typing import Dict

from rich.console import Console
from rich.status import Status

from config import config
from replays.types import Role

console = Console()


class LogStatus(Status):
    name: str
    buffer: str = ""

    def __init__(self, status: str = "", spinner: str = "dots", name: str = None):
        self.name = name
        self.buffer = status
        super().__init__(status, console=console, spinner=spinner)

    def stream(self, message: str):
        self.buffer += message
        self.update(self.buffer)


STATUS_METHODS = ["converse", "transcribe", "playrich", "say"]


class Emojis:
    debug: str = ":bug:"
    info: str = ":information_source:"
    warning: str = ":warning:"
    error: str = ":x:"
    critical: str = ":skull:"
    aicoach: str = ":robot_face:"
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

    _status_methods: Dict[str, LogStatus] = {}

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

        if hasattr(record, "role"):
            if record.role == "assistant":
                emoji = Emojis.aicoach
            else:
                emoji = Emojis.mic

        flush = getattr(record, "flush", False)

        if self.check_stop(record):
            self.stop_statuses()
        elif self.is_status(record):
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

        self.print(msg, emoji=emoji, flush=flush)
        self.fqn = self.get_fqn(record.name, record.funcName)

    def get_fqn(self, name: str, funcName: str):
        return f"{name}.{funcName}"

    def print(self, message, emoji=Emojis.aicoach, flush: bool = False):
        if flush:
            console.print(f"{message}", end="")
        else:
            console.print(f"{emoji} {message}")

    def check_stop(self, record: LogRecord) -> bool:
        for status in self._status_methods.values():
            if status.status == record.msg:
                return True
        return False

    def set_status(self, record: LogRecord) -> None:
        if self.fqn != self.get_fqn(record.name, record.funcName):
            self.stop_statuses()
            # Recreate the status object. If we reuse the same object, the status will render at
            # the position of the last status, overwriting lines printed between the two statuses.
            self._status_methods[record.funcName] = LogStatus(name=record.funcName)

            self._status_methods[record.funcName].start()
            self._status_methods[record.funcName].stream(record.msg)
        else:
            self._status_methods[record.funcName].stream(record.msg)

    def stop_statuses(self):
        for status in self._status_methods.values():
            status.stop()
            status.buffer = ""

        self._status_methods = {}

    def is_status(self, record: LogRecord) -> bool:
        role = getattr(record, "role", None)
        flush = getattr(record, "flush", False)

        if flush == False:
            return False

        if record.funcName in STATUS_METHODS:
            return True

        if flush and role == Role.assistant:
            return True
        return False
