import logging
import threading
from datetime import datetime
from pathlib import Path
from time import sleep

import numpy as np
import pvporcupine
import pyaudio

from log import DEFAULT_LOGGER_NAME
from shared import signal_queue
from src.events import WakeEvent
from src.runtime.settings import Config, get_config

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")

FORMAT = pyaudio.paInt16
CHANNELS = 1


class WakeWordListener(threading.Thread):
    def __init__(self, *, settings: Config | None = None):
        super().__init__()
        self.settings = settings or get_config()
        self.daemon = True
        self._stop_event = threading.Event()
        porcupine_model_path = self.settings.wakeword.porcupine_model_path
        if not porcupine_model_path:
            raise ValueError(
                "Porcupine model path must be provided in settings.wakeword.porcupine_model_path"
            )
        keyword_path = str(Path(__file__).parent.parent.parent / porcupine_model_path)
        access_key = self.settings.wakeword.porcupine_accesskey
        if not access_key:
            raise ValueError(
                "Porcupine access key must be provided in settings.wakeword.porcupine_accesskey"
            )
        if not Path(keyword_path).exists():
            raise FileNotFoundError(f"Porcupine keyword file not found: {keyword_path}")
        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[keyword_path],
        )
        self.audio = pyaudio.PyAudio()
        self.mic_stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=self.porcupine.sample_rate,
            input=True,
            frames_per_buffer=self.porcupine.frame_length,
            input_device_index=self.settings.microphone_index,
        )

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        try:
            self.listen_for_wake_word()
        finally:
            self.porcupine.delete()

    def listen_for_wake_word(self):
        log.debug("Starting porcupine wakeword listener")
        last_score_timestamp = datetime.now()

        while True:
            if self.stopped():
                log.debug("Stopping porcupine wakeword listener")
                break

            audio_frame = np.frombuffer(
                self.mic_stream.read(self.porcupine.frame_length),
                dtype=np.int16,
            )

            keyword_index = self.porcupine.process(audio_frame.tolist())

            if keyword_index >= 0:
                if (datetime.now() - last_score_timestamp).seconds > 5:
                    last_score_timestamp = datetime.now()
                    log.info("Wakeword detected")
                    signal_queue.put(WakeEvent(awake=True))
                    sleep(5)
