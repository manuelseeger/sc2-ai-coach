import io
import logging
import re
from dataclasses import dataclass
from typing import Generator

import numpy as np
import soundfile as sf
import torch
import transformers
import webrtcvad
from scipy.signal import resample
from speech_recognition.audio import AudioData
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from transformers.feature_extraction_utils import BatchFeature
from transformers.models.whisper import WhisperFeatureExtractor
from transformers.utils import is_flash_attn_2_available
from typing_extensions import override

from log import DEFAULT_LOGGER_NAME
from contracts import TranscriberService

transformers.logging.set_verbosity_error()

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")

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


class Transcriber(TranscriberService):
    def __init__(self, *, model_id: str):
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"

        torch.set_default_device(self.device)
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

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

        # Calculate duration of the input audio
        trimmed_duration = len(audio_array) / sample_rate

        # don't transcribe super short clips
        if trimmed_duration < 0.3:
            log.debug(f"Audio too short for transcription: {trimmed_duration:.2f}s")
            return ""

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
        if outputs:
            if isinstance(outputs, dict) and "text" in outputs:
                text_content = outputs["text"]
                if text_content and len(str(text_content)) > 0:
                    output = str(text_content).strip()

        # Apply "thank you" and "I am going to" check using the trimmed duration.
        # Whisper might hallucinate "thank you" for short clips of background noise (clapping like sounds).
        if output:
            match = re.search(r"(?i)\bthank you\b[\s,.;:!?]*", output.lower())
            log.debug(
                f"'thank you' match found: {bool(match)} (Trimmed Duration: {trimmed_duration})"
            )
            if match and trimmed_duration < 0.5:
                return ""

            match_going_to = re.search(r"(?i)\bi.?m going to", output.lower())
            if match_going_to and trimmed_duration < 0.5:
                return ""

        return output
