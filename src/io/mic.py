import logging
from time import time
from typing import TYPE_CHECKING

import speech_recognition as sr
from speech_recognition.audio import AudioData

from src.contracts import MicrophoneService
from src.runtime.audio_devices import get_microphone_name

if TYPE_CHECKING:
    from src.runtime.settings import RecognizerConfig

from log import DEFAULT_LOGGER_NAME

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")


class Microphone(MicrophoneService):
    name: str

    def __init__(
        self,
        *,
        device_index: int | None,
        recognizer_config: "RecognizerConfig",
    ):
        self.device_index = device_index

        self.recognizer = sr.Recognizer()

        self.recognizer.energy_threshold = recognizer_config.energy_threshold
        self.recognizer.pause_threshold = recognizer_config.pause_threshold
        self.recognizer.phrase_threshold = recognizer_config.phrase_threshold
        self.recognizer.non_speaking_duration = recognizer_config.non_speaking_duration

        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5

        microphone_name = get_microphone_name(self.device_index)
        if microphone_name is None:
            microphone_name = "system default input"

        log.debug(f"Using microphone: {microphone_name}")

        self.name = microphone_name

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
