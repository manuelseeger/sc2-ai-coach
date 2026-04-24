from config import TranscriberBackend, config

if config.transcriber_backend == TranscriberBackend.canary_qwen:
    from src.io.transcribe_qwen import QwenTranscriberService as Transcriber
elif config.transcriber_backend == TranscriberBackend.xai:
    from src.io.transcribe_xai import XAITranscriberService as Transcriber
else:
    from src.io.transcribe_whisper import Transcriber

__all__ = ["Transcriber"]
