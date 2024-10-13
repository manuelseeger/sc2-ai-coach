import io
import logging
from typing import List, Optional, Union

import numpy as np
import soundfile as sf
import torch
import transformers
from speech_recognition.audio import AudioData
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from transformers.feature_extraction_utils import BatchFeature
from transformers.models.whisper import WhisperFeatureExtractor
from transformers.utils import TensorType, is_flash_attn_2_available
from typing_extensions import override

from config import config

transformers.logging.set_verbosity_error()

log = logging.getLogger(f"{config.name}.{__name__}")
log.setLevel(logging.DEBUG)


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
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model_id = config.speech_recognition_model
        model_id = "distil-whisper/distil-large-v3"

        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
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
            torch_dtype=torch.float16,
            device=self.device,
            # model_kwargs=self.whisper_params,
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

        length = len(audio_array) / sampling_rate

        outputs = self.pipe(
            audio_array,
            chunk_length_s=30,
            batch_size=24,
        )

        if outputs and "text" in outputs and len(outputs["text"]) > 0:
            output = str(outputs["text"]).strip()

        # Finally discard halucinated 'thank you's on clicks and pops
        if output.lower() == "thank you" and length < 0.7:
            output = ""

        return output
