import torch
from transformers.utils import is_flash_attn_2_available
import numpy as np
import soundfile as sf
import io
from config import config
import logging
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline


log = logging.getLogger(config.name)
log.setLevel(logging.DEBUG)


class Transcriber:
    def __init__(self):
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
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
        )
        log.debug(
            f"Transcriber initialized, Flash-Attn-2: {is_flash_attn_2_available()}, Device: {device}"
        )

    def transcribe(self, audio):
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
