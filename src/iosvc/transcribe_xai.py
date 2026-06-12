import io
import logging

import httpx
import soundfile as sf
from speech_recognition.audio import AudioData

from log import DEFAULT_LOGGER_NAME
from contracts import TranscriberService

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")


STT_URL = "https://api.x.ai/v1/stt"


class XAITranscriberService(TranscriberService):
    def __init__(self, *, api_key: str | None, language: str | None = "en"):
        if not api_key:
            raise ValueError("xai_api_key is required for the xai transcriber backend")
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.language = language
        log.debug("XAITranscriberService initialized")

    def transcribe(self, audio: AudioData) -> str:
        log.info("Transcribing...", extra={"flush": True})
        wav_bytes = audio.get_wav_data(convert_rate=16000)

        audio_array, _ = sf.read(io.BytesIO(wav_bytes))
        duration = len(audio_array) / 16000

        if duration < 0.3:
            log.debug(f"Audio too short for transcription: {duration:.2f}s")
            return ""

        data = {"language": self.language} if self.language else {}
        response = httpx.post(
            STT_URL,
            headers=self.headers,
            files={"file": ("audio.wav", io.BytesIO(wav_bytes), "audio/wav")},
            data=data,
            timeout=30.0,
        )
        response.raise_for_status()

        return response.json().get("text", "").strip()
