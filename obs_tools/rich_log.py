import rich
import logging
from rich.logging import RichHandler
from rich import print
from logging import Handler, LogRecord
from time import sleep

from rich.console import Console

console = Console()


class TwitchHandler(Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last = None

    def emit(self, record: LogRecord) -> None:
        if record.levelno < logging.INFO:
            return

        if self._last == record.msg:
            return

        self._last = record.msg

        console.print(record.msg)

        # if record.msg == "Thinking":
        with console.status("Thinking", spinner="dots"):
            sleep(5)
