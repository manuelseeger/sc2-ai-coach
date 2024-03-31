import os
import click
from time import sleep
from datetime import datetime
import logging
from blinker import signal
from aicoach import AICoach, get_prompt
from obs_tools.parse_map_loading_screen import (
    LoadingScreenScanner,
    get_map_stats,
)

from config import config
from Levenshtein import distance as levenshtein
from replays import NewReplayScanner
from replays.types import Replay
from obs_tools.rich_log import TwitchObsLogHandler
from replays.db import replaydb
from replays.metadata import safe_replay_summary
from replays.types import Role
from rich.prompt import Prompt

log = logging.getLogger(config.name)
log.setLevel(logging.INFO)
log.setLevel(logging.DEBUG)


handler = logging.FileHandler(
    os.path.join("logs", f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-obs_watcher.log"),
)
one_file_handler = logging.FileHandler(
    mode="a",
    filename=os.path.join("logs", "_obs_watcher.log"),
)
log.addHandler(handler)
log.addHandler(one_file_handler)

obs_handler = TwitchObsLogHandler()
log.addHandler(obs_handler)

mic = None
transcriber = None


@click.command()
@click.option("--debug", is_flag=True, help="Debug mode")
@click.option("-v", "--verbose", is_flag=True, help="Verbose mode: print voice input and responses to console")
@click.option("-t", "--textmode", is_flag=True, help="Text mode: run without audio input/output")
def main(debug, verbose, textmode):
    if debug:
        log.setLevel(logging.DEBUG)
        handler.setLevel(logging.DEBUG)
        log.debug("debugging on")

    session = AISession()
    session.verbose = verbose
    session.textmode = textmode

    if not textmode:
        from obs_tools.mic import Microphone
        from aicoach import Transcriber
        from obs_tools.wake import WakeWordListener

        global mic
        mic = Microphone()
        global transcriber
        transcriber = Transcriber()

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
                if datetime.now().second % 10 == 0:
                    if not ping_printed:
                        log.debug("Waiting for thread ...")
                        log.info("Waiting for thread ...")
                        ping_printed = True
                else:
                    ping_printed = False
            sleep(0.1)
        except KeyboardInterrupt:
            break


class AISession:
    coach: AICoach = None
    last_map: str = None
    last_opponent: str = None
    last_mmr: int = 3900
    thread_id: str = None
    last_rep_id: str = None
    verbose: bool = False
    textmode: bool = False

    def __init__(self):
        last_replay = replaydb.get_most_recent()
        self.update_last_replay(last_replay)
        self.coach = AICoach()

    def update_last_replay(self, replay):
        replay = replaydb.get_most_recent()
        self.last_map = replay.map_name
        self.last_opponent = replay.get_player(config.student.name, opponent=True).name
        self.last_mmr = replay.get_player(config.student.name).scaled_rating
        self.last_rep_id = replay.id

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
            if self.textmode:
                prompt = {
                    "text": Prompt.ask(">>>")
                }
            else:
                audio = mic.listen()
                log.debug("Got voice input")
                prompt = transcriber.transcribe(audio)
                if prompt is None or "text" not in prompt or len(prompt["text"]) < 7:
                    continue
                log.debug(prompt["text"])
            
            if self.verbose:
                log.info(prompt["text"], extra={'role': Role.user})

            response = self.chat(prompt["text"])
            log.debug(response)

            if self.verbose:
                log.info(response, extra={'role': Role.assistant})
            
            self.say(response)

            if self.is_goodbye(response):
                return True
            
    def say(self, message):
        if self.textmode:
            log.info(message, extra={'role': Role.assistant})
        else:
            mic.say(message)

    def close(self):
        self.thread_id = None
        self.coach = AICoach()

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
            "replay": str(
                replay.default_projection_json(limit=600, include_workers=False)
            ),
        }
        prompt = get_prompt("prompt_new_replay.txt", replacements)

        with open(
            f"logs/{datetime.now().strftime('%Y%m%d-%H%M%S')}-new_replay.json",
            "w",
            encoding="utf-8",
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

        stats = None
        while stats == None:
            stats = get_map_stats(kw["map"])
            sleep(0.1)

        with open("obs/map_stats.html", "w") as f:
            f.write(stats.prettify())

        if not self.is_active():
            response = self.initiate_from_scanner(
                kw["map"], kw["opponent"], self.last_mmr
            )
            log.debug(f"Response: {response}")
            self.say(response)
            done = self.converse()
            if done:
                self.close()

    def handle_wake(self, sender, **kw):
        if not self.is_active():
            log.debug("Listining for voice input")
            audio = mic.listen()
            log.debug("Got voice input:")
            prompt = transcriber.transcribe(audio)
            log.debug(prompt["text"])
            response = self.initiate_from_voice(prompt["text"])
            log.debug(f"Response: {response}")
            self.say(response)
            done = self.converse()
            if done:
                self.close()

    def handle_new_replay(self, sender, replay: Replay):
        log.debug(sender)
        if not self.is_active():
            log.debug("New replay detected")
            response = self.initiate_from_new_replay(replay)
            log.debug(f"Response: {response}")
            self.say(response)
            done = self.converse()
            if done:
                mic.say("I'll save a summary of the game.")
                self.update_last_replay(replay)

                safe_replay_summary(replay, self.coach)
                
                self.close()


if __name__ == "__main__":
    main()
