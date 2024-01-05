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
from Levenshtein import distance as levenshtein

log = logging.getLogger(config.name)
log.setLevel(logging.INFO)
log.setLevel(logging.DEBUG)

handler = logging.FileHandler(
    os.path.join(
        "logs", f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-obs_watcher.log"
    )
)
log.addHandler(handler)
log.addHandler(RichHandler(level=logging.DEBUG))


mic = Microphone()
transcriber = Transcriber()


@click.command()
@click.option("--debug", is_flag=True, help="Debug mode")
def main(debug):
    if debug:
        log.setLevel(logging.DEBUG)
        handler.setLevel(logging.DEBUG)
        log.debug("debugging on")

    session = AISession()

    listener = WakeWordListener("listener")
    listener.start()

    scanner = LoadingScreenScanner("scanner")
    scanner.start()

    wake = signal("wakeup")
    wake.connect(session.handle_wake)

    loading_screen = signal("loading_screen")
    loading_screen.connect(session.handle_scanner)

    log.info("Starting main loop")
    while True:
        try:
            if session.is_active():
                pass
            else:
                log.debug("Waiting for thread")
            sleep(5)

        except KeyboardInterrupt:
            break


class AISession:
    coach: AICoach = None
    last_map: str = None
    last_opponent: str = None
    last_mmr: int = 3850
    thread_id: str = None

    def __init__(self):
        self.coach = AICoach()

    def initiate_from_scanner(self, map, opponent, mmr) -> str:
        with open(os.path.join("aicoach", "prompt_scanner.txt"), "r") as f:
            prompt = f.read()

        prompt = prompt.replace("{{map}}", str(map))
        prompt = prompt.replace("{{opponent}}", str(opponent))
        prompt = prompt.replace("{{mmr}}", str(mmr))
        self.thread_id = self.coach.current_thread_id

        self.coach.create_thread(prompt)
        run = self.coach.evaluate_run()
        return self.coach.get_most_recent_message()

    def converse(self):
        while True:
            log.info(">>>")
            audio = mic.listen()
            log.debug("Got voice input")
            prompt = transcriber.transcribe(audio)
            log.debug(prompt["text"])
            response = self.coach.chat(prompt["text"])
            log.debug(f"Response: {response}")
            mic.say(response)
            if self.is_goodbye(response):
                log.debug("Goodbye, closing thread")
                self.thread_id = None
                break

    def is_goodbye(self, response):
        if levenshtein(response[-20:].lower().strip(), "good luck, have fun") < 8:
            return True
        else:
            return False

    def initiate_from_voice(self, message: str) -> str:
        self.coach.create_thread(message)
        self.thread_id = self.coach.current_thread_id
        run = self.coach.evaluate_run()
        return self.coach.get_most_recent_message()

    def chat(self, message: str) -> str:
        response = self.coach.chat(message)
        return response

    def is_active(self):
        return self.thread_id is not None

    def handle_scanner(self, sender, **kw):
        log.debug(sender, kw)
        rename_file(config.screenshot, kw["new_name"])
        if not self.is_active():
            response = self.initiate_from_scanner(
                kw["map"], kw["opponent"], self.last_mmr
            )
            log.debug(f"Response: {response}")
            mic.say(response)
            self.converse()

    def handle_wake(self, sender, **kw):
        if not self.is_active():
            log.debug("Listining for voice input")
            audio = mic.listen()
            log.debug("Got voice input:")
            prompt = transcriber.transcribe(audio)
            log.debug(prompt["text"])
            response = self.initiate_from_voice(prompt["text"])
            log.debug(f"Response: {response}")
            mic.say(response)
            self.converse()


if __name__ == "__main__":
    main()
