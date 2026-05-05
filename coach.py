import logging
import queue
import sys
from time import sleep

import click

from config import AIBackend, AudioMode, CoachEvent, config
from log import log
from shared import signal_queue
from src.contracts import MicrophoneService, TranscriberService, TTSService
from src.events import ReplEvent
from src.io.rich_log import RichConsoleLogHandler
from src.session import AISession

rich_handler = RichConsoleLogHandler()
rich_handler.setLevel(logging.INFO)

log.addHandler(rich_handler)


@click.command()
@click.option("--debug", is_flag=True, help="Debug mode")
@click.option("--repl", is_flag=True, help="Start a text-only chat REPL")
@click.option(
    "--trace",
    is_flag=True,
    help="Dump full LLM request and response traces to debug logs",
)
def main(debug, repl, trace):
    if debug:
        log.setLevel(logging.DEBUG)
        log.debug("debugging on")

    if repl:
        config.audiomode = AudioMode.text

    tts, mic, transcriber = _build_services()

    # Build session and initialize event handlers
    # Each handler is a threading.thread that listens for configured events
    # On an event, the handler puts a new task in the signal_queue
    session = AISession(tts=tts, mic=mic, transcriber=transcriber, trace=trace)

    wake = None
    scanner = None
    replay_scanner = None
    twitch = None

    if not repl and CoachEvent.twitch in config.coach_events:
        from src.events import TwitchListener

        twitch = TwitchListener()
        twitch.start()

    if not repl and CoachEvent.wake in config.coach_events:
        from src.events import WakeListener

        wake = WakeListener()
        wake.start()

    if not repl and CoachEvent.game_start in config.coach_events:
        from src.events import GameStartedListener

        scanner = GameStartedListener()
        scanner.start()

    if not repl and CoachEvent.new_replay in config.coach_events:
        from src.events import NewReplayListener

        replay_scanner = NewReplayListener()
        replay_scanner.start()

    if config.audiomode in [AudioMode.voice_out, AudioMode.full] and tts is not None:
        tts.feed("Starting TTS")

    log.info(f"Audio mode: {str(config.audiomode)}")
    log.info(f"OBS integration: {str(config.obs_integration)}")
    log.info(
        f"AI Backend: {str(config.aibackend)} {config.gpt_model if config.aibackend == AIBackend.openai else ''}"
    )
    if config.audiomode in [AudioMode.voice_in, AudioMode.full]:
        log.info(f"Transcriber: {config.transcriber_backend}")
    log.info(f"Coach events enabled: {', '.join(config.coach_events)}")

    log.info(f"Starting {'non-' * (not config.interactive)}interactive session")

    if repl:
        signal_queue.put(ReplEvent())

    # Main loop: Every 1s get a task from the signal_queue first in first out, and let the session process it
    # On shutdown, close all event listener threads and exit
    while True:
        try:
            task = signal_queue.get()
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
                config.audiomode in [AudioMode.voice_out, AudioMode.full]
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
        finally:
            sleep(1)


def _build_services() -> tuple[
    TTSService | None,
    MicrophoneService | None,
    TranscriberService | None,
]:
    tts, mic, transcriber = None, None, None

    if config.audiomode in [AudioMode.voice_in, AudioMode.full] and config.interactive:
        from src.io import Transcriber
        from src.io.mic import Microphone

        mic = Microphone()
        transcriber = Transcriber()

        if "nvidia broadcast" not in mic.name.lower():
            log.warning("Using a non-NVIDIA Broadcast microphone")

    if config.audiomode in [AudioMode.voice_out, AudioMode.full]:
        from src.io.tts import make_tts_stream

        tts = make_tts_stream()
    else:
        from src.io.dummy import TTSDummy

        tts = TTSDummy()

    return tts, mic, transcriber


if __name__ == "__main__":
    main()
