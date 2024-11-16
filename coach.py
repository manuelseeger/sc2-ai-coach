import logging
import queue
import sys
from datetime import datetime, timezone
from time import sleep, time

import click
from Levenshtein import distance as levenshtein
from pydantic import BaseModel
from rich.prompt import Prompt

from aicoach import AICoach
from aicoach.prompt import Templates
from config import AIBackend, AudioMode, CoachEvent, config
from log import log
from obs_tools.playerinfo import resolve_replays_from_current_opponent
from obs_tools.rich_log import TwitchObsLogHandler
from obs_tools.types import ScanResult, TwitchResult, WakeResult
from replays.db import replaydb
from replays.metadata import save_replay_summary
from replays.types import Player, Replay, Role, Session, Usage
from shared import signal_queue

if config.audiomode in [AudioMode.voice_in, AudioMode.full]:
    from aicoach.transcribe import Transcriber
    from obs_tools.mic import Microphone

    mic = Microphone()
    transcriber = Transcriber()

if config.audiomode in [AudioMode.voice_out, AudioMode.full]:
    from obs_tools.tts import make_tts_stream

    tts = make_tts_stream()

if config.obs_integration:
    from obs_tools.mapstats import update_map_stats


obs_handler = TwitchObsLogHandler()
obs_handler.setLevel(logging.INFO)

log.addHandler(obs_handler)


@click.command()
@click.option("--debug", is_flag=True, help="Debug mode")
def main(debug):
    if debug:
        log.setLevel(logging.DEBUG)
        log.debug("debugging on")

    session = AISession()

    if CoachEvent.twitch in config.coach_events:
        from obs_tools.twitch import TwitchListener

        twitch = TwitchListener(name="twitch")
        twitch.start()

    if CoachEvent.wake in config.coach_events:
        from obs_tools import WakeListener

        listener = WakeListener(name="listener")
        listener.start()

    if CoachEvent.game_start in config.coach_events:
        from obs_tools import GameStartedScanner

        scanner = GameStartedScanner(name="scanner")
        scanner.start()

    if CoachEvent.new_replay in config.coach_events:
        from replays.newreplay import NewReplayScanner

        replay_scanner = NewReplayScanner(name="replay_scanner")
        replay_scanner.start()

    if config.audiomode in [AudioMode.voice_out, AudioMode.full]:
        tts.feed("Starting TTS")

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
            task = signal_queue.get()
            # task = None
            if isinstance(task, TwitchResult):
                session.handle_twitch_chat("twitch", task)
            elif isinstance(task, WakeResult):
                session.handle_wake("wakeup", task)
            elif isinstance(task, ScanResult):
                session.handle_game_start("loading_screen", task)
            elif isinstance(task, Replay):
                session.handle_new_replay("replay", task)
            else:
                # print once every 10 seconds so we know you are still alive
                if datetime.now().second % 10 == 0:
                    if not ping_printed:
                        log.info("Waiting for thread ...")
                        ping_printed = True
                else:
                    ping_printed = False

            signal_queue.task_done()
        except queue.Empty:
            pass
        except KeyboardInterrupt:
            log.info("Shutting down ...")

            if session.is_active():
                session.close()
            if config.audiomode in [AudioMode.voice_out, AudioMode.full]:
                tts.stop()
            if CoachEvent.wake in config.coach_events:
                listener.stop()
                listener.join()
            if CoachEvent.game_start in config.coach_events:
                scanner.stop()
                scanner.join()
            if CoachEvent.new_replay in config.coach_events:
                replay_scanner.stop()
                replay_scanner.join()
            if CoachEvent.twitch in config.coach_events:
                twitch.stop()
                twitch.join()
            sys.exit(0)
        finally:
            sleep(1)


class AISession:
    coach: AICoach
    last_map: str
    last_opponent: str
    last_mmr: int = 4000
    _thread_id: str | None = None
    last_rep_id: str
    chat_thread_id: str | None = None

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

    def update_last_replay(self, replay: Replay | None = None):
        if replay is None:
            try:
                replay = replaydb.get_most_recent()
            except:
                log.error("Error getting most recent replay, is DB runnung?")
                sys.exit(1)

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
        return levenshtein(response[-20:].lower().strip(), "good luck, have fun") < 8

    def initiate_from_game_start(self, map, opponent, mmr):
        replacements = {
            "student": str(config.student.name),
            "map": str(map),
            "opponent": str(opponent),
            "mmr": str(mmr),
            "replays": [],
        }

        opponent, past_replays = resolve_replays_from_current_opponent(
            opponent, map, mmr
        )

        if len(past_replays) > 0:
            if past_replays[0].id == self.last_rep_id:
                pass
            replacements["replays"] = [
                r.default_projection_json(limit=300) for r in past_replays[:5]
            ]
            prompt = Templates.scanner.render(replacements)
            self.thread_id = self.coach.create_thread(prompt)
        else:
            self.say(Templates.scanner_empty.render(replacements), flush=False)

    def initiate_from_new_replay(self, replay: Replay):
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
        log.debug(f"{sender} {scanresult}")

        if scanresult.mapname and config.obs_integration:
            update_map_stats(scanresult.mapname)

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

    def handle_twitch_chat(self, sender, twitch_chat: TwitchResult):
        #log.debug(f"{twitch_chat.user}: {twitch_chat.message}")
        log.info(f"{twitch_chat.user}: {twitch_chat.message}")

        while self.is_active():
            sleep(1)

        replacements = {
            "user": twitch_chat.user,
            "message": twitch_chat.message,
        }
        prompt = Templates.twitch.render(replacements)

        class TwitchChatResponse(BaseModel):
            is_question: bool
            answer: str

        if not self.chat_thread_id:
            self.chat_thread_id = self.coach.create_thread()
        else:
            self.coach.set_active_thread(self.chat_thread_id)

        self.thread_id = self.chat_thread_id

        response: TwitchChatResponse = self.coach.get_structured_response(
            message=prompt,
            schema=TwitchChatResponse,
            additional_instructions=Templates.init_twitch.render(
                {"student": config.student.name}
            ),
        )

        log.debug(response)

        if response.is_question:
            self.say(response.answer, flush=False)

        self.close()


if __name__ == "__main__":
    main()
