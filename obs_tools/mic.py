import speech_recognition as sr
from typing import Dict
import logging
import pyttsx3
from config import config

log = logging.getLogger(config.name)


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

        self.voiceengine = pyttsx3.init()
        voices = self.voiceengine.getProperty("voices")
        self.voiceengine.setProperty("voice", voices[3].id if len(voices) > 3 else voices[0].id)

    def listen(self):
        with self.microphone as source:
            audio = self.recognizer.listen(source)
            log.debug("Got voice input")
        return audio

    def say(self, text):
        self.voiceengine.say(text)
        self.voiceengine.runAndWait()
