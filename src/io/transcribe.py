import io
import logging
import re
from typing import Generator

import numpy as np
import soundfile as sf
import torch
import transformers
import webrtcvad
from pydantic.dataclasses import dataclass
from scipy.signal import resample
from speech_recognition.audio import AudioData
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from transformers.feature_extraction_utils import BatchFeature
from transformers.models.whisper import WhisperFeatureExtractor
from transformers.utils import is_flash_attn_2_available
from typing_extensions import override

from config import config

transformers.logging.set_verbosity_error()

log = logging.getLogger(f"{config.name}.{__name__}")
log.setLevel(logging.DEBUG)

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


class GPUWhisperFeatureExtractor(WhisperFeatureExtractor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"

    @override
    def __call__(
        self,
        *args,
        **kwargs,
    ) -> BatchFeature:
        return super().__call__(*args, device=self.device, **kwargs)


class Transcriber:
    def __init__(self):
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"

        torch.set_default_device(self.device)
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model_id = config.speech_recognition_model

        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=self.torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
            attn_implementation="flash_attention_2",
            use_flash_attention_2=True,
        )
        self.model.to(self.device)

        self.processor = AutoProcessor.from_pretrained(model_id)

        extractor = GPUWhisperFeatureExtractor(
            feature_size=self.processor.feature_extractor.feature_size
        )

        self.whisper_params = {"temperature": 0.2}

        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=self.model,
            tokenizer=self.processor.tokenizer,
            feature_extractor=extractor,
            max_new_tokens=128,
            chunk_length_s=30,
            batch_size=16,
            torch_dtype=self.torch_dtype,
            device=self.device,
            model_kwargs=self.whisper_params,
        )
        log.debug(
            f"Transcriber initialized, Device: {self.device}, Flash-Attn-2: {is_flash_attn_2_available()}"
        )

    def transcribe(self, audio: AudioData) -> str:
        log.info("Transcribing...", extra={"flush": True})
        wav_bytes = audio.get_wav_data(convert_rate=16000)
        wav_stream = io.BytesIO(wav_bytes)
        audio_array, sampling_rate = sf.read(wav_stream)
        audio_array = audio_array.astype(np.float16)

        sample_rate = 16000

        # Generate frames and detect speech frames using VAD.
        frames = list(
            frame_generator(
                audio=audio.frame_data, frame_duration_ms=30, sample_rate=sample_rate
            )
        )
        speech_flags = [vad.is_speech(frame.data, sample_rate) for frame in frames]

        # Identify the first and last frame indices with speech.
        speech_indices = [i for i, flag in enumerate(speech_flags) if flag]
        if not speech_indices:
            return ""
        first_idx, last_idx = speech_indices[0], speech_indices[-1]
        start_time = frames[first_idx].timestamp
        end_time = frames[last_idx].timestamp + frames[last_idx].duration
        trimmed_duration = end_time - start_time

        # Convert start_time/end_time to sample indices.
        # start_sample = int(start_time * sample_rate)
        # end_sample = int(end_time * sample_rate)
        # trimmed_audio = audio_array[start_sample:end_sample]

        outputs = self.pipe(
            audio_array,
            chunk_length_s=30,
            batch_size=24,
        )

        output = ""
        if outputs and "text" in outputs and len(outputs["text"]) > 0:
            output = str(outputs["text"]).strip()

        # Apply "thank you" check using the trimmed duration.
        if output:
            match = re.search(r"(?i)\bthank you\b[\s,.;:!?]*", output.lower())
            log.debug(
                f"'thank you' match found: {bool(match)} (Trimmed Duration: {trimmed_duration})"
            )
            # if trimmed_duration < 0.15:
            ##    output = ""
        return output
