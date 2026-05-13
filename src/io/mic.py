import logging
from time import time
from typing import TYPE_CHECKING

import pyaudio
import speech_recognition as sr
from speech_recognition.audio import AudioData

from src.contracts import MicrophoneService

if TYPE_CHECKING:
    from src.runtime.settings import RecognizerConfig

log = logging.getLogger(__name__)


def _get_audio() -> pyaudio.PyAudio:
    return pyaudio.PyAudio()


class Microphone(MicrophoneService):
    name: str

    def __init__(self, *, device_index: int, recognizer_config: "RecognizerConfig"):
        self.device_index = device_index

        self.recognizer = sr.Recognizer()

        self.recognizer.energy_threshold = recognizer_config.energy_threshold
        self.recognizer.pause_threshold = recognizer_config.pause_threshold
        self.recognizer.phrase_threshold = recognizer_config.phrase_threshold
        self.recognizer.non_speaking_duration = recognizer_config.non_speaking_duration

        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5

        # log the selected audio device:
        audio = _get_audio()
        dev = audio.get_device_info_by_index(self.device_index)
        log.debug(f"Using microphone: {dev['name']}")

        self.name = str(dev["name"])

        self.microphone = sr.Microphone(device_index=self.device_index)

    def listen(self) -> AudioData | None:
        start_time = time()
        while True:
            with self.microphone as source:
                try:
                    audio: AudioData = self.recognizer.listen(source, timeout=20)  # type: ignore stream=False does not return Generator
                    return audio
                except sr.WaitTimeoutError:
                    continue

            if time() - start_time > 60:
                return None
