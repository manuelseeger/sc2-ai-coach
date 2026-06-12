import logging
import queue
import sys

import click

from log import configure_application_logging, log
from shared import signal_queue
from contracts import (
    LiveEventListener,
    MicrophoneService,
    TranscriberService,
    TTSService,
)
from events.events import ReplEvent
from persistence.runtime import build_persistence_services
from runtime.playeridentity import build_player_identity_services
from runtime.settings import (
    AudioMode,
    Config,
    TranscriberBackend,
    get_config,
)
from session import AISession


def load_runtime_settings() -> "Config":
    return get_config()


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

    configure_application_logging(logger=log)
    _install_rich_log_handler(log)
    persistence = build_persistence_services(settings)
    player_identity = build_player_identity_services(
        settings,
        replay_store=persistence.replay_store,
    )

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
        settings=settings,
        tts=tts,
        mic=mic,
        transcriber=transcriber,
        trace=trace,
        conversation_store=persistence.conversation_store,
        replay_store=persistence.replay_store,
        session_store=persistence.session_store,
        player_resolver=player_identity.resolver,
    )

    wake, scanner, replay_scanner, twitch = _build_live_event_listeners(
        settings,
        replay_store=persistence.replay_store,
        player_identity_enricher=player_identity.enricher,
        repl=repl,
    )

    for listener in [twitch, wake, scanner, replay_scanner]:
        if listener is not None:
            listener.start()

    if settings.audiomode in [AudioMode.voice_out, AudioMode.full] and tts is not None:
        tts.feed("Starting TTS")

    log.info(f"Audio mode: {str(settings.audiomode)}")
    log.info(f"OBS integration: {str(settings.obs_integration)}")
    log.info(f"AI Backend: {str(settings.aibackend)} {settings.gpt_model}")
    if settings.audiomode in [AudioMode.voice_in, AudioMode.full]:
        log.info(f"Microphone: {mic.name if mic is not None else 'none'}")
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


def _install_rich_log_handler(log: logging.Logger) -> None:
    from iosvc.rich_log import RichConsoleLogHandler

    if any(isinstance(handler, RichConsoleLogHandler) for handler in log.handlers):
        return

    rich_handler = RichConsoleLogHandler()
    rich_handler.setLevel(logging.INFO)
    log.addHandler(rich_handler)


def _build_io_services(
    settings: "Config",
) -> tuple[
    TTSService | None,
    MicrophoneService | None,
    TranscriberService | None,
]:
    tts, mic, transcriber = None, None, None

    if (
        settings.audiomode in [AudioMode.voice_in, AudioMode.full]
        and settings.interactive
    ):
        from iosvc.mic import Microphone

        mic = Microphone(
            device_index=settings.microphone_index,
            recognizer_config=settings.recognizer,
        )
        transcriber = _build_transcriber(settings)
        logging.getLogger(__name__).info(f"Using microphone: {mic.name}")

    if settings.audiomode in [AudioMode.voice_out, AudioMode.full]:
        from iosvc.tts import make_tts_stream

        tts = make_tts_stream(tts_config=settings.tts)
    else:
        from iosvc.dummy import TTSDummy

        tts = TTSDummy()

    return tts, mic, transcriber


def _build_live_event_listeners(
    settings: "Config",
    *,
    replay_store,
    player_identity_enricher,
    repl: bool,
) -> tuple[
    LiveEventListener | None,
    LiveEventListener | None,
    LiveEventListener | None,
    LiveEventListener | None,
]:
    from runtime.settings import CoachEvent

    wake = None
    scanner = None
    replay_scanner = None
    twitch = None

    if repl:
        return wake, scanner, replay_scanner, twitch

    if CoachEvent.twitch in settings.coach_events:
        from events.twitch import TwitchListener

        twitch = TwitchListener(settings=settings)

    if CoachEvent.wake in settings.coach_events:
        if (
            settings.audiomode in [AudioMode.full, AudioMode.voice_in]
            and settings.interactive
        ):
            from events.wake_livekit import WakeWordListener

            wake = WakeWordListener(settings=settings)
        else:
            from events.wake_key import WakeKeyListener

            wake = WakeKeyListener(settings=settings)

    if CoachEvent.game_start in settings.coach_events:
        if settings.obs_integration:
            from events.loading_screen import NewMatchListener

            scanner = NewMatchListener(settings=settings)
        else:
            from events.clientapi import ClientAPIListener

            scanner = ClientAPIListener(settings=settings)

    if CoachEvent.new_replay in settings.coach_events:
        from events.newreplay import NewReplayListener

        replay_scanner = NewReplayListener(
            settings=settings,
            replay_store=replay_store,
            player_identity_enricher=player_identity_enricher,
        )

    return wake, scanner, replay_scanner, twitch


def _build_transcriber(settings: "Config") -> TranscriberService:
    if settings.transcriber_backend == TranscriberBackend.canary_qwen:
        from iosvc.transcribe_qwen import QwenTranscriberService

        return QwenTranscriberService()

    if settings.transcriber_backend == TranscriberBackend.xai:
        from iosvc.transcribe_xai import XAITranscriberService

        return XAITranscriberService(
            api_key=settings.xai_api_key,
            language=settings.xai_stt_language,
        )

    from iosvc.transcribe_whisper import Transcriber

    return Transcriber(model_id=settings.speech_recognition_model)


if __name__ == "__main__":
    main()
