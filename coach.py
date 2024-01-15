from dotenv import load_dotenv

load_dotenv()
import os
import click
from time import sleep
from datetime import datetime
import logging
from blinker import signal
from aicoach import AICoach, Transcriber, get_prompt
from obs_tools.wake import WakeWordListener
from obs_tools.parse_map_loading_screen import LoadingScreenScanner, rename_file
from obs_tools.mic import Microphone
from typing import Dict
from rich import print
from rich.logging import RichHandler
from config import config
from Levenshtein import distance as levenshtein
from replays import NewReplayScanner
from replays.types import Replay


log = logging.getLogger(config.name)
log.setLevel(logging.INFO)
log.setLevel(logging.DEBUG)

# log everything including stacktrace to a file:
handler = logging.FileHandler(
    os.path.join("logs", f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-obs_watcher.log"),
)
log.addHandler(handler)
log.addHandler(
    RichHandler(level=logging.DEBUG, show_time=False, markup=True, show_path=False)
)


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

    replay_scanner = NewReplayScanner("replay_scanner")
    replay_scanner.start()

    wake = signal("wakeup")
    wake.connect(session.handle_wake)

    loading_screen = signal("loading_screen")
    loading_screen.connect(session.handle_scanner)

    new_replay = signal("replay")
    new_replay.connect(session.handle_new_replay)

    log.info("Starting main loop")

    ping_printed = False
    while True:
        try:
            if session.is_active():
                pass
            else:
                # print once every 10 seconds so we know you are still alive
                if datetime.now().second % 10 == 0 and not ping_printed:
                    log.debug("Waiting for thread")
                    ping_printed = True
                else:
                    ping_printed = False

            sleep(0.1)

        except KeyboardInterrupt:
            break


def singleton(cls):
    instances = {}

    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return wrapper


@singleton
class AISession:
    coach: AICoach = None
    last_map: str = None
    last_opponent: str = None
    last_mmr: int = 3850
    thread_id: str = None
    last_rep_id: str = None

    def __init__(self):
        self.coach = AICoach()

    def initiate_from_scanner(self, map, opponent, mmr) -> str:
        replacements = {
            "student": str(config.student.name),
            "map": str(map),
            "opponent": str(opponent),
            "mmr": str(mmr),
        }

        prompt = get_prompt("prompt_scanner.txt", replacements)

        self.coach.create_thread(prompt)
        self.thread_id = self.coach.current_thread_id
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
            log.debug(f"Response:\n{response}")
            mic.say(response)
            if self.is_goodbye(response):
                log.debug(f"Goodbye, closing thread {self.thread_id}")
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

    def initiate_from_new_replay(self, replay: Replay) -> str:
        opponent = (
            replay.players[0].name
            if replay.players[1].name == config.student.name
            else replay.players[1].name
        )
        replacements = {
            "student": str(config.student.name),
            "map": str(replay.map_name),
            "opponent": str(opponent),
            "replay": str(replay.default_projection_json()),
        }
        prompt = get_prompt("prompt_new_replay.txt", replacements)

        with open(
            f"logs/{datetime.now().strftime('%Y%m%d-%H%M%S')}-new_replay.json", "w"
        ) as f:
            f.write(prompt)

        self.coach.create_thread(prompt)
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

    def handle_new_replay(self, sender, replay: Replay):
        log.debug(sender)
        if not self.is_active():
            log.debug("New replay detected")
            response = self.initiate_from_new_replay(replay)
            log.debug(f"Response: {response}")
            mic.say(response)
            self.converse()


if __name__ == "__main__":
    main()
