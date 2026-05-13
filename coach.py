import logging
import queue
import sys
import types
from functools import partial
from typing import TYPE_CHECKING

import click

from src.contracts import MicrophoneService, TranscriberService, TTSService

if TYPE_CHECKING:
    from src.runtime.settings import Config


@click.command()
@click.option("--debug", is_flag=True, help="Debug mode")
@click.option("--repl", is_flag=True, help="Start a text-only chat REPL")
@click.option(
    "--trace",
    is_flag=True,
    help="Dump full LLM request and response traces to debug logs",
)
def main(debug, repl, trace):
    settings = load_runtime_settings()
    _install_legacy_config(settings)

    from log import log
    from shared import signal_queue
    from src.events.events import ReplEvent
    from src.persistence.runtime import build_persistence_services
    from src.playerinfo import save_player_info
    from src.runtime.settings import AudioMode, CoachEvent
    from src.session import AISession

    _install_rich_log_handler(log)
    persistence = build_persistence_services(settings)

    if debug:
        log.setLevel(logging.DEBUG)
        log.debug("debugging on")

    if repl:
        settings.audiomode = AudioMode.text
        signal_queue.put(ReplEvent())

    tts, mic, transcriber = _build_io_services(settings)

    # Build session and initialize event handlers
    # Each handler is a threading.thread that listens for configured events
    # On an event, the handler puts a new task in the signal_queue
    session = AISession(
        tts=tts,
        mic=mic,
        transcriber=transcriber,
        trace=trace,
        conversation_store=persistence.conversation_store,
        replay_store=persistence.replay_store,
        session_store=persistence.session_store,
    )

    wake = None
    scanner = None
    replay_scanner = None
    twitch = None

    if not repl and CoachEvent.twitch in settings.coach_events:
        from src.events import TwitchListener

        twitch = TwitchListener()
        twitch.start()

    if not repl and CoachEvent.wake in settings.coach_events:
        from src.events import WakeListener

        wake = WakeListener()
        wake.start()

    if not repl and CoachEvent.game_start in settings.coach_events:
        from src.events import GameStartedListener

        scanner = GameStartedListener()
        scanner.start()

    if not repl and CoachEvent.new_replay in settings.coach_events:
        from src.events import NewReplayListener

        replay_scanner = NewReplayListener(
            replay_store=persistence.replay_store,
            save_player_info_fn=partial(
                save_player_info,
                replay_store=persistence.replay_store,
            ),
        )
        replay_scanner.start()

    if settings.audiomode in [AudioMode.voice_out, AudioMode.full] and tts is not None:
        tts.feed("Starting TTS")

    log.info(f"Audio mode: {str(settings.audiomode)}")
    log.info(f"OBS integration: {str(settings.obs_integration)}")
    log.info(f"AI Backend: {str(settings.aibackend)} {settings.gpt_model}")
    if settings.audiomode in [AudioMode.voice_in, AudioMode.full]:
        log.info(f"Transcriber: {settings.transcriber_backend}")
    log.info(f"Coach events enabled: {', '.join(settings.coach_events)}")

    log.info(f"Starting {'non-' * (not settings.interactive)}interactive session")

    # Main loop: Every 1s get a task from the signal_queue first in first out, and let the session process it
    # On shutdown, close all event listener threads and exit
    while True:
        try:
            task = signal_queue.get(timeout=0.5)
            session.handle(task)
            signal_queue.task_done()
            if repl and isinstance(task, ReplEvent):
                return
        except queue.Empty:
            pass
        except KeyboardInterrupt:
            log.info("Shutting down ...")

            if session.is_active():
                session.close()
            if (
                settings.audiomode in [AudioMode.voice_out, AudioMode.full]
                and tts is not None
            ):
                tts.stop()
            if wake is not None:
                wake.stop()
                wake.join()
            if scanner is not None:
                scanner.stop()
                scanner.join()
            if replay_scanner is not None:
                replay_scanner.stop()
                replay_scanner.join()
            if twitch is not None:
                twitch.stop()
                twitch.join()
            sys.exit(0)


def load_runtime_settings() -> "Config":
    from src.runtime.settings import load_current_settings

    return load_current_settings()


def _install_legacy_config(settings: "Config") -> None:
    from src.runtime import settings as runtime_settings

    legacy_config = types.ModuleType("config")
    for name, value in runtime_settings.__dict__.items():
        if name.startswith("_"):
            continue
        setattr(legacy_config, name, value)

    legacy_config.config = settings
    legacy_config.Config = type(settings)
    legacy_config.SettingsLoaderError = runtime_settings.SettingsLoaderError
    legacy_config.load_current_settings = runtime_settings.load_current_settings
    sys.modules["config"] = legacy_config


def _install_rich_log_handler(log: logging.Logger) -> None:
    from src.io.rich_log import RichConsoleLogHandler

    if any(isinstance(handler, RichConsoleLogHandler) for handler in log.handlers):
        return

    rich_handler = RichConsoleLogHandler()
    rich_handler.setLevel(logging.INFO)
    log.addHandler(rich_handler)


def _build_io_services(settings: "Config") -> tuple[
    TTSService | None,
    MicrophoneService | None,
    TranscriberService | None,
]:
    from src.runtime.settings import AudioMode

    tts, mic, transcriber = None, None, None

    if settings.audiomode in [AudioMode.voice_in, AudioMode.full] and settings.interactive:
        from src.io.mic import Microphone

        mic = Microphone(
            device_index=settings.microphone_index,
            recognizer_config=settings.recognizer,
        )
        transcriber = _build_transcriber(settings)

        if "nvidia broadcast" not in mic.name.lower():
            logging.getLogger(__name__).warning(
                "Using a non-NVIDIA Broadcast microphone"
            )

    if settings.audiomode in [AudioMode.voice_out, AudioMode.full]:
        from src.io.tts import make_tts_stream

        tts = make_tts_stream(tts_config=settings.tts)
    else:
        from src.io.dummy import TTSDummy

        tts = TTSDummy()

    return tts, mic, transcriber


def _build_transcriber(settings: "Config") -> TranscriberService:
    from src.runtime.settings import TranscriberBackend

    if settings.transcriber_backend == TranscriberBackend.canary_qwen:
        from src.io.transcribe_qwen import QwenTranscriberService

        return QwenTranscriberService()

    if settings.transcriber_backend == TranscriberBackend.xai:
        from src.io.transcribe_xai import XAITranscriberService

        return XAITranscriberService(
            api_key=settings.xai_api_key,
            language=settings.xai_stt_language,
        )

    from src.io.transcribe_whisper import Transcriber

    return Transcriber(model_id=settings.speech_recognition_model)


if __name__ == "__main__":
    main()
