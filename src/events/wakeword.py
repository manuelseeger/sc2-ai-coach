import logging
import threading
from datetime import datetime
from time import sleep

import numpy as np
import onnxruntime
import pyaudio
import torch
from openwakeword.model import Model

from config import config
from shared import signal_queue
from src.events import WakeEvent

onnxruntime.set_default_logger_severity(3)

log = logging.getLogger(f"{config.name}.{__name__}")

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280
MIC_INDEX = 2
audio = pyaudio.PyAudio()
mic_stream = audio.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK,
    input_device_index=MIC_INDEX,
)

owwModel = Model([config.oww_model], inference_framework="onnx")


class WakeWordListener(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self._stop_event = threading.Event()

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
            audio = np.frombuffer(mic_stream.read(CHUNK), dtype=np.int16)

            prediction = owwModel.predict(audio)

            score = prediction[config.oww_model]

            if score > config.oww_sensitivity:
                if (datetime.now() - last_score_timestamp).seconds > 5:
                    last_score_timestamp = datetime.now()
                    log.info(f"Model woke up with a score of {score:.2f}")
                    signal_queue.put(WakeEvent(awake=True))
                    owwModel.reset()
                    sleep(5)
