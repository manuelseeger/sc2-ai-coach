import logging
import os
import warnings
from datetime import datetime

from config import config

warnings.filterwarnings("ignore")

from rich.traceback import install

install(show_locals=True)

rootlogger = logging.getLogger()
for handler in rootlogger.handlers.copy():
    try:
        rootlogger.removeHandler(handler)
    except ValueError:
        pass
rootlogger.addHandler(logging.NullHandler())

log = logging.getLogger(config.name)
log.propagate = False
log.setLevel(logging.DEBUG)


if not os.path.exists("logs"):
    os.makedirs("logs")


class FlushFilter(logging.Filter):
    def filter(self, record):
        return not hasattr(record, "flush")


flush_filter = FlushFilter()

handler = logging.FileHandler(
    os.path.join(
        "logs",
        f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-obs_watcher.log",
    ),
    encoding="utf-8",
)
handler.setLevel(logging.DEBUG)
handler.addFilter(flush_filter)

one_file_handler = logging.FileHandler(
    mode="a",
    filename=os.path.join("logs", "_obs_watcher.log"),
    encoding="utf-8",
)
one_file_handler.setLevel(logging.DEBUG)
one_file_handler.addFilter(flush_filter)

log.addHandler(handler)
log.addHandler(one_file_handler)
