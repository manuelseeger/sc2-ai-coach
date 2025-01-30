import sys

# add parent dir to path
sys.path.append(".")
import logging
from time import sleep

from config import config
from src.io.rich_log import RichConsoleLogHandler
from src.replaydb.types import Role

log = logging.getLogger(config.name)
log.setLevel(logging.INFO)
log.addHandler(RichConsoleLogHandler())


def playrich():

    # paragraph with 3 sentences
    para = "This is a test. This is only a test. Had this been an actual emergency, you would have been instructed where to tune in your area for news and official information."

    tokens = para.split()

    for token in tokens:
        log.info(token + " ", extra={"role": Role.assistant, "flush": True})
        sleep(0.1)

    another_function()


def another_function():
    log.info("This is another function")


if __name__ == "__main__":
    playrich()
