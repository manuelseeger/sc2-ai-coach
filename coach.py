import logging
import queue
import sys
from datetime import datetime
from time import sleep, time
from typing import Callable

import click
from Levenshtein import distance as levenshtein
from openai.types.beta.threads import Message
from pydantic import BaseModel
from rich.prompt import Prompt

from config import AIBackend, AudioMode, CoachEvent, config
from log import log
from shared import signal_queue
from src.ai import AICoach
from src.ai.prompt import Templates
from src.events import (
    NewReplayEvent,
    NewMatchEvent,
    TwitchChatEvent,
    TwitchFollowEvent,
    TwitchRaidEvent,
    WakeEvent,
)
from src.io.rich_log import RichConsoleLogHandler
from src.playerinfo import resolve_replays_from_current_opponent
from src.replaydb.db import eq, replaydb
from src.replaydb.types import AssistantMessage, Metadata, Replay, Role, Session, Usage
from src.smurfs import get_sc2pulse_match_history

# Setup: Input output, logging, depending on config
if config.audiomode in [AudioMode.voice_in, AudioMode.full]:
    from src.io.mic import Microphone
    from src.io.transcribe import Transcriber

    mic = Microphone()
    transcriber = Transcriber()

if config.audiomode in [AudioMode.voice_out, AudioMode.full]:
    from src.io.tts import make_tts_stream

    tts = make_tts_stream()

if config.obs_integration:
    from src.mapstats import update_map_stats


rich_handler = RichConsoleLogHandler()
rich_handler.setLevel(logging.INFO)

log.addHandler(rich_handler)


@click.command()
@click.option("--debug", is_flag=True, help="Debug mode")
def main(debug):
    if debug:
        log.setLevel(logging.DEBUG)
        log.debug("debugging on")

    # Build session and initialize event handlers
    # Each handler is a threading.thread that listens for configured events
    # On an event, the handler puts a new task in the signal_queue
    session = AISession()

    if CoachEvent.twitch in config.coach_events:
        from src.events import TwitchListener

        twitch = TwitchListener(name="twitch")
        twitch.start()

    if CoachEvent.wake in config.coach_events:
        from src.events import WakeListener

        listener = WakeListener(name="listener")
        listener.start()

    if CoachEvent.game_start in config.coach_events:
        from src.events import GameStartedListener

        scanner = GameStartedListener(name="scanner")
        scanner.start()

    if CoachEvent.new_replay in config.coach_events:
        from src.events import NewReplayListener

        replay_scanner = NewReplayListener()
        replay_scanner.start()

    if config.audiomode in [AudioMode.voice_out, AudioMode.full]:
        tts.feed("Starting TTS")

    log.info(f"Audio mode: {str(config.audiomode)}")
    log.info(f"OBS integration: {str(config.obs_integration)}")
    log.info(
        f"AI Backend: {str(config.aibackend)} {config.gpt_model if config.aibackend == AIBackend.openai else ''}"
    )
    if config.audiomode in [AudioMode.voice_in, AudioMode.full]:
        log.info(f"Transcriber: {config.speech_recognition_model}")
    log.info(f"Coach events enabled: {', '.join(config.coach_events)}")

    log.info(f"Starting { 'non-' * ( not config.interactive ) }interactive session")

    # Main loop: Every 1s get a task from the signal_queue first in first out, and let the session process it
    # On shutdown, close all event listener threads and exit
    while True:
        try:
            task = signal_queue.get()
            session.handle(task)
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
    """Represents one gaming session with the AI coach.

    Holds some session state:
    - current assistant thread
    - current thread handling twitch chat
    - last player + replay we faced

    Records the session in the replaydb, and calculates the usage and cost
    of the AI backend.

    Implements the handlers for the different event types.

    Each handler usually sets up a new conversation by grounding the context
    with the event data. Then the handler starts the conversation between user
    and AI coach.

    So for each event type there is a handler method, and optionally an init method.
    The init method sets up the conversation context, and the handler method starts
    and ends the conversation.
    Once a conversation is ended, the handler exits and the main loop can pull and
    process a new task."""

    coach: AICoach
    last_map: str
    last_opponent: str
    last_mmr: int = 4000
    _thread_id: str | None = None
    last_rep_id: str
    chat_thread_id: str | None = None

    session: Session

    handlers: dict[type, Callable]

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

        self.handlers = {
            TwitchChatEvent: self.handle_twitch_chat,
            TwitchFollowEvent: self.handle_twitch_follow,
            TwitchRaidEvent: self.handle_twitch_raid,
            WakeEvent: self.handle_wake,
            NewMatchEvent: self.handle_game_start,
            NewReplayEvent: self.handle_new_replay,
        }

    def get_handler(self, task) -> Callable | None:
        return self.handlers.get(type(task))

    def handle(self, task):
        handler = self.get_handler(task)
        if handler:
            handler(task)

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
        """Listen to input from the user, pass it to the AI coach, and output
        the response.
        Exit once AI coach thinks the conversation is over.
        """

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

    def stream_thread(self) -> str:
        """Stream an active thead with the AI coach, and output the response.

        Additionally return the buffered response as string."""
        buffer = ""
        for message in self.coach.stream_thread():
            buffer += message
            self.say(message)
        return buffer

    def chat(self, message: str) -> str:
        """Input the message to AI coach, and output the response.

        Additionally return the buffered response as string."""
        buffer = ""
        for response in self.coach.chat(message):
            buffer += response
            self.say(response)
        return buffer

    def say(self, message, flush=True):
        """Output a message to the user. Depending on audio config, this uses
        text-to-speech or just writes to the rich log."""
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
        """Calculate the usage and cost of the AI backend for the current thread
        and save it to the session in the DB."""
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
        """Adds game start information to conversation context

        The context is initialized depending on:

        Is this a rematch / have we just played this player before?
        Do we have past replay of this opponent?
        Can we identify the opponent from past games or by opponent match history?
        """

        replacements = {
            "student": str(config.student.name),
            "map": str(map),
            "opponent": str(opponent),
            "mmr": str(mmr),
            "replays": [],
            "race_report": "",
        }
        prompt = None
        match_history = None

        playerinfo, past_replays = resolve_replays_from_current_opponent(
            opponent, map, mmr
        )

        if playerinfo is not None:
            match_history = get_sc2pulse_match_history(playerinfo.toon_handle)
            if match_history is not None and len(match_history):
                match_history.data.to_csv(
                    f"logs/match_history_{opponent}_{playerinfo.toon_handle}.csv",
                    index=False,
                    encoding="utf-8",
                )
                race_report = match_history.race_report
                replacements["race_report"] = race_report.to_markdown(index=False)

        if len(past_replays) > 0:
            if past_replays[0].id == self.last_rep_id:
                replacements["replays"] = [
                    past_replays[0].default_projection_json(limit=300)
                ]
                prompt = Templates.rematch.render(replacements)
            else:
                replacements["replays"] = [
                    r.default_projection_json(limit=300) for r in past_replays[:5]
                ]
                prompt = Templates.new_game.render(replacements)

        if match_history and prompt is None:
            prompt = Templates.new_game.render(replacements)

        if prompt is not None:
            self.thread_id = self.coach.create_thread(prompt)
        else:
            self.say(Templates.new_game_empty.render(replacements), flush=False)

    def initiate_from_new_replay(self, replay: Replay):
        """Adds replay information to conversation context"""

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

    def handle_game_start(self, scanresult: NewMatchEvent):
        """Handle new game event.

        This is invoked when a new match is started in SC2.

        Sets up context with past information about the player we are facing,
        if available. Then starts a conversation.
        """
        log.debug(scanresult)

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
        else:
            log.debug("active thread, skipping")

    def handle_wake(self, wakeresult: WakeEvent):
        """Handle a wake event.

        This is the user waking up the assistant for a conversation
        without additional context.
        """

        log.debug(wakeresult)
        if not self.is_active():
            self.thread_id = self.coach.create_thread()

            done = self.converse()
            if done:
                self.close()
        else:
            log.debug("active thread, skipping")

    def handle_new_replay(self, replay_result: NewReplayEvent):
        """Handle a new replay event.

        This is invoked when a new replay is added to the replay folder.
        Adds the replay to the context and starts a conversation.
        """

        replay = replay_result.replay

        log.debug(replay)
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

                self.save_replay_summary(replay)

                self.close()
        else:
            log.debug("active thread, skipping")

    def handle_twitch_follow(self, twitch_follow: TwitchFollowEvent):
        """Handle a twitch follow event.

        Thanks the follower.
        """

        log.debug(f"{twitch_follow.user} followed")
        replacements = {
            "user": twitch_follow.user,
            "student": config.student.name,
        }
        prompt = Templates.twitch_follow.render(replacements)
        self.thread_id = self.coach.create_thread(prompt)
        response = self.stream_thread()
        log.info(response, extra={"role": Role.assistant})
        self.close()

    def handle_twitch_raid(self, twitch_raid: TwitchRaidEvent):
        """Handle a twitch raid event.

        Thanks the raider and welcomes the viewers
        """

        log.debug(f"{twitch_raid.user} raided with {twitch_raid.viewers} viewers")
        replacements = {
            "user": twitch_raid.user,
            "viewers": twitch_raid.viewers,
            "student": config.student.name,
        }
        prompt = Templates.twitch_raid.render(replacements)
        self.thread_id = self.coach.create_thread(prompt)
        response = self.stream_thread()
        log.info(response, extra={"role": Role.assistant})
        self.close()

    def handle_twitch_chat(self, twitch_chat: TwitchChatEvent):
        """Handle a twitch chat event.

        If a viewer says something in chat, figure out if the message is a question, and
        if so, answer it.

        This is different than the other event handlers in that the assistent reuses the same
        thread for all chat messages, so that it can properly answer follow up questions. So
        AICoach keeps a memory of the entire chat history.
        """

        log.debug(f"{twitch_chat.user}: {twitch_chat.message}")

        replacements = {
            "user": twitch_chat.user,
            "message": twitch_chat.message,
        }
        prompt = Templates.twitch_chat.render(replacements)

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
            log.info(f"{twitch_chat.user}: {twitch_chat.message}")
            self.say(response.answer, flush=False)

        self.close()

    def save_replay_summary(self, replay: Replay):

        messages: list[Message] = self.coach.get_conversation()

        class Response(BaseModel):
            summary: str
            keywords: list[str]

        response = self.coach.get_structured_response(
            message=Templates.summary.render(), schema=Response
        )

        log.info(f"Added tags '{','.join(response.keywords)} to replay'")
        meta: Metadata = Metadata(replay=replay.id, description=response.summary)
        meta.tags = response.keywords
        meta.conversation = [
            AssistantMessage(
                role=m.role,
                text=m.content[0].text.value,
                created_at=datetime.fromtimestamp(m.created_at),
            )
            # skip the instruction message which includes the replay as JSON
            for m in messages[::-1][1:]
            if m.content[0].text.value
        ]

        replaydb.db.save(meta, query=eq(Metadata.replay, replay.id))


if __name__ == "__main__":
    main()
