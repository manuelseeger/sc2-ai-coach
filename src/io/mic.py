import logging
from time import time

import numpy as np
import speech_recognition as sr
from speech_recognition.audio import AudioData

from config import config

log = logging.getLogger(f"{config.name}.{__name__}")


class Microphone:
    def __init__(self, device_index=None):
        if device_index is None:
            device_index = config.microphone_index
        self.device_index = device_index

        self.recognizer = sr.Recognizer()

        self.recognizer.energy_threshold = config.recognizer.energy_threshold
        self.recognizer.pause_threshold = config.recognizer.pause_threshold
        self.recognizer.phrase_threshold = config.recognizer.phrase_threshold
        self.recognizer.non_speaking_duration = config.recognizer.non_speaking_duration

        self.microphone = sr.Microphone(device_index=self.device_index)

    def listen(self) -> AudioData:
        start_time = time()
        while True:
            with self.microphone as source:
                audio = self.recognizer.listen(source)

                return audio

            if time() - start_time > 60 * 3:
                return None
