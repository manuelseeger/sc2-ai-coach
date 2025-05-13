import logging
import queue
import sys
from time import sleep

import click

from config import AIBackend, AudioMode, CoachEvent, config
from log import log
from shared import signal_queue
from src.io.rich_log import RichConsoleLogHandler
from src.session import AISession

tts, mic, transcriber = None, None, None

# Setup: Input output, logging, depending on config
if config.audiomode in [AudioMode.voice_in, AudioMode.full]:
    from src.io.mic import Microphone
    from src.io.transcribe import Transcriber

    mic = Microphone()
    transcriber = Transcriber()

if config.audiomode in [AudioMode.voice_out, AudioMode.full]:
    from src.io.tts import make_tts_stream

    tts = make_tts_stream()

else:
    from src.io.dummy import TTSDummy

    tts = TTSDummy()

if config.obs_integration:
    pass


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
    session = AISession(tts=tts, mic=mic, transcriber=transcriber)

    if CoachEvent.twitch in config.coach_events:
        from src.events import TwitchListener

        twitch = TwitchListener()
        twitch.start()

    if CoachEvent.wake in config.coach_events:
        from src.events import WakeListener

        listener = WakeListener()
        listener.start()

    if CoachEvent.game_start in config.coach_events:
        from src.events import GameStartedListener

        scanner = GameStartedListener()
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

    log.info(f"Starting {'non-' * (not config.interactive)}interactive session")

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


if __name__ == "__main__":
    main()
