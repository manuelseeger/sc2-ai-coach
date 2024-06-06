import logging
from typing import Generator

import numpy as np
import speech_recognition as sr
import webrtcvad
from pydantic.dataclasses import dataclass
from scipy.signal import resample
from speech_recognition.audio import AudioData

from config import config

log = logging.getLogger(f"{config.name}.{__name__}")

vad = webrtcvad.Vad()


@dataclass
class Frame:
    """Represents a "frame" of audio data."""

    data: bytes
    timestamp: float
    duration: float


def frame_generator(
    audio: bytes, frame_duration_ms: float, sample_rate: int
) -> Generator[Frame, None, None]:
    """Generates audio frames from PCM audio data.

    Takes the desired frame duration in milliseconds, the PCM data, and
    the sample rate.

    Yields Frames of the requested duration.
    """
    audio_array = np.frombuffer(audio, dtype=np.int16).astype(np.float32)

    # Downsample from 44100Hz to 16000Hz
    original_rate = 44100
    target_rate = 16000
    downsampled_audio = resample(
        audio_array, int(len(audio_array) * target_rate / original_rate)
    )

    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n < len(downsampled_audio):
        yield Frame(audio[offset : offset + n], timestamp, duration)
        timestamp += duration
        offset += n


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
        while True:
            with self.microphone as source:
                audio = self.recognizer.listen(source)

            sample_rate = 16000

            frames = frame_generator(
                audio=audio.frame_data, frame_duration_ms=30, sample_rate=sample_rate
            )

            # For each frame get an indicator if it is speech or not
            is_speech_frames = [
                vad.is_speech(frame.data, sample_rate) for frame in frames
            ]

            # Calculate the percentage of speech frames
            # This is an attempt to counter whisper halucinations. Ambient noise, especially clapping
            # or clacking (keyboard) can be halucinated as "Thank you" by whisper. We preprocess with
            # VAD to figure out if the audio is truly speech or just noise.
            speech_indicator = sum(is_speech_frames) / len(is_speech_frames)

            if speech_indicator > config.recognizer.speech_threshold:
                return audio
