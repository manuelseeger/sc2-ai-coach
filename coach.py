import logging
import os
import sys
import warnings
from datetime import datetime, timezone
from time import sleep, time

import click
from blinker import signal
from Levenshtein import distance as levenshtein
from rich.prompt import Prompt

from aicoach import AICoach
from aicoach.prompt import Templates
from config import AIBackend, AudioMode, CoachEvent, config
from obs_tools.playerinfo import resolve_replays_from_current_opponent
from obs_tools.rich_log import TwitchObsLogHandler
from obs_tools.types import ScanResult, WakeResult
from replays.db import replaydb
from replays.metadata import save_replay_summary
from replays.types import Player, Replay, Role, Session, Usage

warnings.filterwarnings("ignore")


rootlogger = logging.getLogger()
for handler in rootlogger.handlers.copy():
    try:
        rootlogger.removeHandler(handler)
    except ValueError:
        pass
rootlogger.addHandler(logging.NullHandler())

log = logging.getLogger(config.name)
log.propagate = False
log.setLevel(logging.INFO)

if config.audiomode in [AudioMode.voice_in, AudioMode.full]:
    from aicoach.transcribe import Transcriber
    from obs_tools.mic import Microphone

    mic = Microphone()
    transcriber = Transcriber()


if config.obs_integration:
    from obs_tools.mapstats import get_map_stats

if not os.path.exists("logs"):
    os.makedirs("logs")

handler = logging.FileHandler(
    os.path.join(
        "logs",
        f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-obs_watcher.log",
    ),
    encoding="utf-8",
)
handler.setLevel(logging.DEBUG)
one_file_handler = logging.FileHandler(
    mode="a",
    filename=os.path.join("logs", "_obs_watcher.log"),
    encoding="utf-8",
)
one_file_handler.setLevel(logging.DEBUG)
log.addHandler(handler)
log.addHandler(one_file_handler)

obs_handler = TwitchObsLogHandler()
obs_handler.setLevel(logging.INFO)
log.addHandler(obs_handler)


@click.command()
@click.option("--debug", is_flag=True, help="Debug mode")
def main(debug):
    if debug:
        log.setLevel(logging.DEBUG)
        handler.setLevel(logging.DEBUG)
        log.debug("debugging on")

    if config.audiomode in [AudioMode.voice_out, AudioMode.full]:
        from obs_tools.tts import make_tts_stream

        global tts

        tts = make_tts_stream()
        tts.feed("")

    session = AISession()

    if CoachEvent.wake in config.coach_events:
        from obs_tools import WakeListener

        listener = WakeListener(name="listener")
        listener.start()
        wake = signal("wakeup")
        wake.connect(session.handle_wake)

    if CoachEvent.game_start in config.coach_events:
        from obs_tools import GameStartedScanner

        scanner = GameStartedScanner(name="scanner")
        scanner.start()
        loading_screen = signal("loading_screen")
        loading_screen.connect(session.handle_game_start)

    if CoachEvent.new_replay in config.coach_events:
        from replays.newreplay import NewReplayScanner

        replay_scanner = NewReplayScanner(name="replay_scanner")
        replay_scanner.start()
        new_replay = signal("replay")
        new_replay.connect(session.handle_new_replay)

    log.info("\n")
    log.info(f"Audio mode: {str(config.audiomode)}")
    log.info(f"OBS integration: {str(config.obs_integration)}")
    log.info(
        f"AI Backend: {str(config.aibackend)} {config.gpt_model if config.aibackend == AIBackend.openai else ''}"
    )
    log.info(f"Coach events enabled: {', '.join(config.coach_events)}")

    log.info(f"Starting { 'non-' * ( not config.interactive ) }interactive session")

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

            sleep(1)
        except KeyboardInterrupt:
            log.info("Shutting down ...")

            if session.is_active():
                session.close()

            if CoachEvent.wake in config.coach_events:
                listener.stop()
                listener.join()
            if CoachEvent.game_start in config.coach_events:
                scanner.stop()
                scanner.join()
            if CoachEvent.new_replay in config.coach_events:
                replay_scanner.stop()
                replay_scanner.join()
            sys.exit(0)


class AISession:
    coach: AICoach = None
    last_map: str = None
    last_opponent: str = None
    last_mmr: int = 4000
    _thread_id: str = None
    last_rep_id: str = None

    session: Session

    def __init__(self):

        self.update_last_replay()
        self.coach = AICoach()

        self.session = Session(
            session_date=datetime.now(),
            completion_pricing=config.gpt_completion_pricing,
            prompt_pricing=config.gpt_prompt_pricing,
            ai_backend=config.aibackend,
        )
        replaydb.db.save(self.session)

    @property
    def thread_id(self):
        return self._thread_id

    @thread_id.setter
    def thread_id(self, value):
        self._thread_id = value
        if value is not None:
            self.session.threads.append(value)
            replaydb.db.save(self.session)

    def update_last_replay(self, replay: Replay = None):
        if replay is None:
            replay = replaydb.get_most_recent()
        if replay is None:
            log.warning(
                f"Can't find most recent replay for student '{config.student.name}'"
            )
            return
        self.last_map = replay.map_name
        self.last_opponent = replay.get_player(config.student.name, opponent=True).name
        self.last_mmr = replay.get_player(config.student.name).scaled_rating
        self.last_rep_id = replay.id

    def converse(self):

        if not config.interactive:
            sleep(1)
            log.info("No input, closing thread")
            sleep(1)
            return True

        start_time = time()
        while True:
            if time() - start_time > 60 * 3:
                log.info("No input, closing thread")
                return True
            if config.audiomode in [AudioMode.voice_in, AudioMode.full]:
                audio = mic.listen()
                if audio is None:
                    continue
                log.debug("Got voice input")

                text = transcriber.transcribe(audio)
                if len(text) < 7:
                    continue
                log.debug(text)
            else:
                text = Prompt.ask(
                    config.student.emoji,
                )
            log.info(text, extra={"role": Role.user})

            response = self.chat(text)
            log.info(response, extra={"role": Role.assistant})

            if self.is_goodbye(response):
                return True

    def stream_thread(self):
        buffer = ""
        for message in self.coach.stream_thread():
            buffer += message
            self.say(message)
        return buffer

    def chat(self, message: str) -> str:
        buffer = ""
        for response in self.coach.chat(message):
            buffer += response
            self.say(response)

        return buffer

    def say(self, message, flush=True):
        if config.audiomode in [AudioMode.text, AudioMode.voice_in]:
            log.info(message, extra={"role": Role.assistant, "flush": flush})
        else:
            log.info(message, extra={"role": Role.assistant, "flush": flush})
            tts.feed(message)

    def close(self):
        log.info("Closing thread")
        self.calculate_usage()
        self.thread_id = None

    def is_active(self):
        return self.thread_id is not None

    def calculate_usage(self):
        if not self.thread_id:
            return
        token_usage = self.coach.get_thread_usage(self.thread_id)

        prompt_price = round(token_usage.prompt_tokens * config.gpt_prompt_pricing, 2)
        completion_price = round(
            token_usage.completion_tokens * config.gpt_completion_pricing, 2
        )
        prompt_price = prompt_price if prompt_price > 0 else 0.01
        completion_price = completion_price if completion_price > 0 else 0.01

        log.info(
            f"Total tokens: {token_usage.total_tokens} (~${(prompt_price + completion_price):.2f})"
        )
        usage = Usage(
            completion_tokens=token_usage.completion_tokens,
            prompt_tokens=token_usage.prompt_tokens,
            total_tokens=token_usage.total_tokens,
            thread_id=self.thread_id,
        )
        self.session.usages.append(usage)
        replaydb.db.save(self.session)

    def is_goodbye(self, response: str):
        if levenshtein(response[-20:].lower().strip(), "good luck, have fun") < 8:
            return True
        else:
            return False

    def initiate_from_game_start(self, map, opponent, mmr) -> str:
        replacements = {
            "student": str(config.student.name),
            "map": str(map),
            "opponent": str(opponent),
            "mmr": str(mmr),
        }

        opponent, past_replays = resolve_replays_from_current_opponent(opponent, map)

        if len(past_replays) > 0:
            replacements["replays"] = [
                r.default_projection_json(limit=300) for r in past_replays[:5]
            ]
            prompt = Templates.scanner.render(replacements)
            self.thread_id = self.coach.create_thread(prompt)
        else:
            self.say(Templates.scanner_empty.render(replacements), flush=False)

    def initiate_from_new_replay(self, replay: Replay) -> str:
        opponent = replay.get_opponent_of(config.student.name).name
        replacements = {
            "student": str(config.student.name),
            "map": str(replay.map_name),
            "opponent": str(opponent),
            "replay": str(
                replay.default_projection_json(limit=600, include_workers=False)
            ),
        }
        prompt = Templates.new_replay.render(replacements)

        self.thread_id = self.coach.create_thread(prompt)

    def handle_game_start(self, sender, scanresult: ScanResult):
        log.debug(sender, scanresult)

        if scanresult.mapname and config.obs_integration:
            stats = get_map_stats(scanresult.mapname)
            if stats is not None:
                with open("obs/map_stats.html", "w") as f:
                    f.write(stats.prettify())

        if not self.is_active():
            self.initiate_from_game_start(
                scanresult.mapname, scanresult.opponent, self.last_mmr
            )
            if self.is_active():
                response = self.stream_thread()
                log.info(response, extra={"role": Role.assistant})
                done = self.converse()
                if done:
                    self.close()

    def handle_wake(self, sender, wakeresult: WakeResult):
        log.debug(sender)
        if not self.is_active():
            self.thread_id = self.coach.create_thread()

            done = self.converse()
            if done:
                self.close()

    def handle_new_replay(self, sender, replay: Replay):
        log.debug(sender)
        if not self.is_active():
            log.debug("New replay detected")
            self.initiate_from_new_replay(replay)
            response = self.stream_thread()
            log.info(response, extra={"role": Role.assistant})
            done = self.converse()
            if done:
                sleep(2)
                self.say("I'll save a summary of the game.", flush=False)
                self.update_last_replay(replay)

                save_replay_summary(replay, self.coach)

                self.close()


if __name__ == "__main__":
    main()
