import torch
from transformers import pipeline
import numpy as np
import soundfile as sf
import io


class Transcriber:
    def __init__(self):
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-large-v3",
            torch_dtype=torch.float16,
            device="cuda:0",
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
