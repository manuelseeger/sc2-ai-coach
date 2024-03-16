import pyttsx3
import sys


def init_voice_engine():
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    engine.setProperty("voice", voices[3].id if len(voices) > 3 else voices[0].id)
    return engine


def say(s):
    engine.say(s)
    engine.runAndWait()  # In here the program will wait as if is in main file


if __name__ == "__main__":
    if len(sys.argv) > 1:
        engine = init_voice_engine()

        say(str(sys.argv[1]))
    else:
        print("Usage: python3 mic.py <text>")
else:

    import speech_recognition as sr
    from typing import Dict
    import logging
    from config import config
    from subprocess import call, Popen
    import os

    log = logging.getLogger(f"{config.name}.{__name__}")
    log.setLevel(logging.DEBUG)

    class Microphone:
        def __init__(self, device_index=None):
            if device_index is None:
                device_index = config.microphone_index
            self.device_index = device_index

            self.recognizer = sr.Recognizer()

            self.recognizer.energy_threshold = config.recognizer.energy_threshold
            self.recognizer.pause_threshold = config.recognizer.pause_threshold
            self.recognizer.phrase_threshold = config.recognizer.phrase_threshold
            self.recognizer.non_speaking_duration = (
                config.recognizer.non_speaking_duration
            )

            self.microphone = sr.Microphone(device_index=self.device_index)

        def listen(self):
            with self.microphone as source:
                audio = self.recognizer.listen(source)
            return audio

        def say_(self, text):
            self.voiceengine.say(text)
            ret = self.voiceengine.runAndWait()
            log.debug(f"Done speaking")

        def say(self, text):
            # runandwait is broken and hangs the program
            # so we speak in a subprocess
            Popen([sys.executable, "obs_tools/mic.py", text], cwd=os.getcwd())
