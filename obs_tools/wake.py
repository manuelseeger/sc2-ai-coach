import openwakeword
import pyaudio
import numpy as np
from openwakeword.model import Model
import yaml
import threading
from blinker import signal

config: dict = yaml.safe_load(open("config.yml"))

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

owwModel = Model([config.get("oww_model")], inference_framework="onnx")


class WakeWordListener(threading.Thread):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def run(self):
        while True:
            # Get audio
            audio = np.frombuffer(mic_stream.read(CHUNK), dtype=np.int16)

            # Feed to openWakeWord model
            prediction = owwModel.predict(audio)

            wakeup = signal("wakeup")

            for mdl in owwModel.prediction_buffer.keys():
                # Add scores in formatted table
                scores = list(owwModel.prediction_buffer[mdl])
                curr_score = format(scores[-1], ".20f").replace("-", "")

                for score in scores:
                    if score > 0.5:
                        print(
                            f"Model {mdl} woke up with a score of {format(score, '.20f')}"
                        )
                        wakeup.send(self)
