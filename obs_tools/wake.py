import pyaudio
import numpy as np
from openwakeword.model import Model
import threading
from blinker import signal
from config import config
import logging

log = logging.getLogger(config.name)

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

    def run(self):
        while True:
            audio = np.frombuffer(mic_stream.read(CHUNK), dtype=np.int16)

            prediction = owwModel.predict(audio)

            for mdl in owwModel.prediction_buffer.keys():

                scores = list(owwModel.prediction_buffer[mdl])

                for score in scores:
                    if score > 0.5:
                        log.info(f"Model {mdl} woke up with a score of {score}")
                        wakeup.send(self)
