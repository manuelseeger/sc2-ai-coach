import io
import logging

import numpy as np
import soundfile as sf
import torch
import transformers
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from transformers.utils import is_flash_attn_2_available

from config import config

transformers.logging.set_verbosity_error()

log = logging.getLogger(f"{config.name}.{__name__}")
log.setLevel(logging.DEBUG)


class Transcriber:
    def __init__(self):
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        torch.set_default_device(device)
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model_id = config.speech_recognition_model

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
            attn_implementation="flash_attention_2",
        )
        model.to(device)

        processor = AutoProcessor.from_pretrained(model_id)

        # don't let whisper halucinate, see https://github.com/openai/whisper/discussions/679
        whisper_params = {"temperature": 0.2}

        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            max_new_tokens=128,
            chunk_length_s=30,
            batch_size=16,
            torch_dtype=torch.float16,
            device=device,
            model_kwargs=whisper_params,
        )
        log.debug(
            f"Transcriber initialized, Device: {device}, Flash-Attn-2: {is_flash_attn_2_available()}"
        )

    def transcribe(self, audio):
        log.info("Transcribing...")
        wav_bytes = audio.get_wav_data(convert_rate=16000)
        wav_stream = io.BytesIO(wav_bytes)
        audio_array, sampling_rate = sf.read(wav_stream)
        audio_array = audio_array.astype(np.float16)

        outputs = self.pipe(
            audio_array,
            chunk_length_s=30,
            batch_size=24,
        )
        return outputs
