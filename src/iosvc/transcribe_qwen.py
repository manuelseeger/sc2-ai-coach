import io
import logging
import os
import re
import tempfile

import numpy as np
import soundfile as sf
from speech_recognition.audio import AudioData

from log import DEFAULT_LOGGER_NAME
from contracts import TranscriberService

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")

MODEL_ID = "nvidia/canary-qwen-2.5b"


class QwenTranscriberService(TranscriberService):
    def __init__(self):
        from nemo.collections.speechlm2.models import SALM

        self.model = SALM.from_pretrained(MODEL_ID)
        log.debug(f"QwenTranscriberService initialized with model: {MODEL_ID}")

    def transcribe(self, audio: AudioData) -> str:
        log.info("Transcribing...", extra={"flush": True})
        wav_bytes = audio.get_wav_data(convert_rate=16000)
        wav_stream = io.BytesIO(wav_bytes)
        audio_array, _ = sf.read(wav_stream)
        audio_array = audio_array.astype(np.float32)

        if audio_array.ndim > 1:
            audio_array = audio_array.mean(axis=1)

        sample_rate = 16000
        duration = len(audio_array) / sample_rate

        if duration < 0.3:
            log.debug(f"Audio too short for transcription: {duration:.2f}s")
            return ""

        # Model supports max 40 seconds
        if duration > 40.0:
            log.debug(f"Audio exceeds 40s ({duration:.2f}s), truncating")
            audio_array = audio_array[: int(40.0 * sample_rate)]

        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
        try:
            os.close(tmp_fd)
            sf.write(tmp_path, audio_array, sample_rate)

            answer_ids = self.model.generate(
                prompts=[
                    [
                        {
                            "role": "user",
                            "content": f"Transcribe the following: {self.model.audio_locator_tag}",
                            "audio": [tmp_path],
                        }
                    ]
                ],
                max_new_tokens=128,
            )
        finally:
            os.unlink(tmp_path)

        output = ""
        if answer_ids is not None:
            output = self.model.tokenizer.ids_to_text(answer_ids[0].cpu()).strip()

        if output:
            match = re.search(r"(?i)\bthank you\b[\s,.;:!?]*", output.lower())
            log.debug(
                f"'thank you' match found: {bool(match)} (Duration: {duration:.2f}s)"
            )
            if match and duration < 0.5:
                return ""

            match_going_to = re.search(r"(?i)\bi.?m going to", output.lower())
            if match_going_to and duration < 0.5:
                return ""

        return output
