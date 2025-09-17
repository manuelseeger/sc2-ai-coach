import sys
from datetime import datetime
from time import sleep, time
from typing import Callable

from Levenshtein import distance as levenshtein
from openai.types.beta.threads import Message, TextContentBlock
from pydantic import BaseModel
from rich.prompt import Prompt

from config import AudioMode, config
from log import log
from src.ai import AICoach
from src.ai.prompt import Templates
from src.contracts import MicrophoneService, TranscriberService, TTSService
from src.events import (
    CastReplayEvent,
    NewMatchEvent,
    NewReplayEvent,
    TwitchChatEvent,
    TwitchFollowEvent,
    TwitchRaidEvent,
    WakeEvent,
)
from src.lib.sc2client import SC2Client
from src.lib.sc2pulse import SC2PulseClient, get_division_for_mmr
from src.mapstats import update_map_stats
from src.matchhistory import get_sc2pulse_match_history
from src.playerinfo import resolve_replays_from_current_opponent
from src.replaydb.db import eq, replaydb
from src.replaydb.types import AssistantMessage, Metadata, Replay, Role, Session, Usage
from src.util import secs2time


class DummyMicrophoneService(MicrophoneService):
    def listen(self) -> None:
        return None


class DummyTranscriberService(TranscriberService):
    def transcribe(self, audio) -> str:
        return ""


class DummyTTSService(TTSService):
    def feed(self, text: str) -> None:
        pass

    def stop(self) -> None:
        pass

    def is_speaking(self) -> bool:
        return False


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

    tts: TTSService
    mic: MicrophoneService
    transcriber: TranscriberService

    def __init__(self, tts=None, mic=None, transcriber=None):
        self.update_last_replay()
        self.set_season()
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
            CastReplayEvent: self.handle_cast_replay,
        }

        # Assign services or dummy implementations
        self.tts = tts if tts is not None else DummyTTSService()
        self.mic = mic if mic is not None else DummyMicrophoneService()
        self.transcriber = (
            transcriber if transcriber is not None else DummyTranscriberService()
        )

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

    def set_season(self):
        sc2pulse = SC2PulseClient()
        season = sc2pulse.get_current_season()
        log.info(
            f"Current SC2 season is {season.year}-{season.number}, started {season.start.date()}"
        )
        config.season_start = season.start

    def update_last_replay(self, replay: Replay | None = None):
        if replay is None:
            try:
                replay = replaydb.get_most_recent()
            except:  # noqa: E722
                log.error("Error getting most recent replay, is DB running?")
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
                audio = self.mic.listen()
                if audio is None:
                    continue
                log.debug("Got voice input")

                text = self.transcriber.transcribe(audio)
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
        log.info(message, extra={"role": Role.assistant, "flush": flush})
        self.tts.feed(message)

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

    def handle_cast_replay(self, cast_result: CastReplayEvent):
        """Handle a cast replay event.

        This is invoked by the AI coach itself via a function call, when it is asked to cast a replay.

        Intro is deterministic from replay data. User / student needs to hit play on the
        replay as the intro is being read out, since AI coach does not have access to game state.
        """
        replay = cast_result.replay

        sc2client = SC2Client()
        sc2pulse = SC2PulseClient()

        # init cast instructions with replay data
        opponent = replay.get_opponent_of(config.student.name)
        player = replay.get_player(config.student.name)

        replacements = {
            "replay": str(
                replay.default_projection_json(limit=1000, include_workers=True)
            ),
        }
        prompt = Templates.cast_replay.render(replacements)
        self.coach.init_additional_instructions(prompt)
        self.thread_id = self.coach.create_thread("00:00")

        # collect intro data and start with intro
        matchup = player.play_race + " vs " + opponent.play_race
        league_bounds = sc2pulse.get_league_bounds()
        division = get_division_for_mmr(
            player.scaled_rating, league_bounds=league_bounds
        )
        intro_replacements = {
            "student": str(config.student.name),
            "student_color": player.color.name,
            "student_position": str(player.clock_position),
            "map": str(replay.map_name),
            "opponent": str(opponent.name),
            "opponent_color": opponent.color.name,
            "opponent_position": str(opponent.clock_position),
            "league": f"{division[0]} {division[1]}",
            "matchup": matchup,
        }
        intro = Templates.cast_intro.render(intro_replacements)
        self.coach.add_message(intro, role="assistant")
        self.say(intro)

        # start the game and commentate
        while True:
            gameinfo = sc2client.wait_for_gameinfo()
            if gameinfo is None:
                msg = "SC2 game client is not running, cannot cast replay"
                log.error(msg)
                self.say(msg)
                self.close()
                return

            if gameinfo.displayTime >= replay.real_length:
                break

            timestamp = secs2time(gameinfo.displayTime)
            response = self.chat(timestamp)
            log.debug(f"{timestamp}: {response}")

            while self.tts.is_speaking():
                sleep(1)

        summary = self.chat(
            "The game is over. Give us a nice outro for winner and loser and a very short summary of the game."
        )
        self.say(summary)
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
                role=Role(m.role),
                text=m.content[0].text.value,
                created_at=datetime.fromtimestamp(m.created_at),
            )
            # skip the instruction message which includes the replay as JSON
            for m in messages[::-1][1:]
            if isinstance(m.content[0], TextContentBlock)
            if m.content[0].text.value
        ]

        replaydb.db.save(meta, query=eq(Metadata.replay, replay.id))  # pyright: ignore[reportArgumentType]
