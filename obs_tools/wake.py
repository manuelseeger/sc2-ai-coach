import pyaudio
import numpy as np
from openwakeword.model import Model
import threading
from blinker import signal
from config import config
import logging
from time import sleep
from datetime import datetime
import onnxruntime

onnxruntime.set_default_logger_severity(3)

log = logging.getLogger(config.name)
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

wakeup = signal("wakeup")


class WakeWordListener(threading.Thread):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.daemon = True

    def run(self):
        self.listen_for_wake_word()

    def listen_for_wake_word(self):
        log.debug("Starting wakeword listener")
        last_score_timestamp = datetime.now()
        while True:
            audio = np.frombuffer(mic_stream.read(CHUNK), dtype=np.int16)

            prediction = owwModel.predict(audio)

            score = prediction[config.oww_model]

            if score > config.oww_sensitivity:
                if (datetime.now() - last_score_timestamp).seconds > 5:
                    last_score_timestamp = datetime.now()
                    log.info(f"Model woke up with a score of {score:.2f}")
                    wakeup.send(self)
                    owwModel.reset()
                    sleep(5)
