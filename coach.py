from dotenv import load_dotenv

load_dotenv()
import os
from obs_tools.parse_map_loading_screen import (
    parse_map_loading_screen,
    parse_map_stats,
    clean_map_name,
)
import click
from time import sleep

import datetime
import re
import yaml
import logging
import sys
import rich
from aicoach import AICoach
from obs_tools.wake import WakeWordListener
from obs_tools.parse_map_loading_screen import LoadingScreenScanner

config = yaml.safe_load(open("config.yml"))

log = logging.getLogger(__name__)

handler = logging.FileHandler(
    os.path.join("logs", f"{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}-obs_watcher.log")
)
log.addHandler(handler)
from blinker import signal

cleanf = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
clean_clan = re.compile(r"<(.+)>\s+(.*)")

barcode = "llllllllll"


@click.command()
@click.option("--screenshot", help="Screenshow file to look for")
@click.option("--runfor", help="Player to start conversation about")
@click.option("--withcoach", is_flag=True, help="Run with AI coach")
@click.option("--debug", is_flag=True, help="Debug mode")
def main(screenshot, runfor, withcoach, debug):
    if debug:
        log.setLevel(logging.INFO)
        handler.setLevel(logging.INFO)
        log.debug("debugging on")

    if withcoach:
        coach = AICoach()

    if screenshot:
        pass

    listener = WakeWordListener('listener')
    listener.start()

    scanner = LoadingScreenScanner('scanner')
    scanner.start()

    while True:
        try:
            print("waiting")
            sleep(5)

        except KeyboardInterrupt:
            break

filename = config.get("screenshot")

def handle(sender, **kw):
    print(sender, kw)

    if sender.name == "scanner":
        path, _ = os.path.split(filename)
        os.rename(filename, os.path.join(path, kw['new_name']))


wake = signal("wakeup")
wake.connect(handle)

loading_screen = signal("loading_screen")
loading_screen.connect(handle)

if __name__ == "__main__":
    main()
