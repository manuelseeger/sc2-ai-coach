import logging
import threading
from datetime import datetime
from time import sleep

import numpy as np
import onnxruntime
import pyaudio
import torch
from openwakeword.model import Model

from shared import signal_queue
from src.events import WakeEvent
from src.runtime.settings import Config, load_current_settings

onnxruntime.set_default_logger_severity(3)

from log import DEFAULT_LOGGER_NAME

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280


class WakeWordListener(threading.Thread):
    def __init__(self, *, settings: Config | None = None):
        super().__init__()
        self.settings = settings or load_current_settings()
        self.daemon = True
        self._stop_event = threading.Event()
        self.audio = pyaudio.PyAudio()
        self.mic_stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=self.settings.microphone_index,
        )
        self.oww_model = Model(
            [self.settings.wakeword.model],
            inference_framework="onnx",
        )  # type: ignore[arg-type]

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        torch.set_default_device(device)
        self.listen_for_wake_word()

    def listen_for_wake_word(self):
        log.debug("Starting wakeword listener")
        last_score_timestamp = datetime.now()
        while True:
            if self.stopped():
                log.debug("Stopping wakeword listener")
                break
            audio = np.frombuffer(self.mic_stream.read(CHUNK), dtype=np.int16)

            prediction = self.oww_model.predict(audio)

            score = prediction[self.settings.wakeword.model]  # type: ignore[index]

            if score > self.settings.wakeword.sensitivity:
                if (datetime.now() - last_score_timestamp).seconds > 5:
                    last_score_timestamp = datetime.now()
                    log.info("Wakeword detected")
                    signal_queue.put(WakeEvent(awake=True))
                    self.oww_model.reset()
                    sleep(5)
