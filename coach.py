from dotenv import load_dotenv

load_dotenv()
import os
import click
from time import sleep
import datetime
import logging
import sys
from blinker import signal
from aicoach import AICoach, Transcriber
from obs_tools.wake import WakeWordListener
from obs_tools.parse_map_loading_screen import LoadingScreenScanner, rename_file
from obs_tools.mic import Microphone
from typing import Dict
from rich import print
from rich.logging import RichHandler
from config import config

log = logging.getLogger(config.name)

handler = logging.FileHandler(
    os.path.join(
        "logs", f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-obs_watcher.log"
    )
)
log.addHandler(handler)
log.addHandler(RichHandler())


mic = Microphone()
transcriber = Transcriber()
coach = AICoach()


@click.command()
# @click.option("--runfor", help="Player to start conversation about")
# @click.option("--withcoach", is_flag=True, help="Run with AI coach")
@click.option("--debug", is_flag=True, help="Debug mode")
def main(debug):
    if debug:
        log.setLevel(logging.INFO)
        handler.setLevel(logging.INFO)
        log.debug("debugging on")

    listener = WakeWordListener("listener")
    listener.start()

    scanner = LoadingScreenScanner("scanner")
    scanner.start()

    while True:
        try:
            print("waiting")
            sleep(5)

        except KeyboardInterrupt:
            break


def handle_scanner(sender, **kw):
    log.debug(sender, kw)
    filename = config.get("screenshot")
    rename_file(filename, kw["new_name"])


def handle_wake(sender, **kw):
    log.debug(sender, kw)
    audio = mic.listen()
    log.debug("Got voice input")
    prompt = transcriber.transcribe(audio)
    log.debug("Transcribed voice input")
    print(prompt)


wake = signal("wakeup")
wake.connect(handle_wake)

loading_screen = signal("loading_screen")
loading_screen.connect(handle_scanner)

if __name__ == "__main__":
    main()
