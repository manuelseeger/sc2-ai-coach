from config import TranscriberBackend, config


def _load_transcriber():
    if config.transcriber_backend == TranscriberBackend.canary_qwen:
        from src.io.transcribe_qwen import QwenTranscriberService

        return QwenTranscriberService
    if config.transcriber_backend == TranscriberBackend.xai:
        from src.io.transcribe_xai import XAITranscriberService

        return XAITranscriberService

    from src.io.transcribe_whisper import Transcriber

    return Transcriber


def __getattr__(name: str):
    if name == "Transcriber":
        return _load_transcriber()
    raise AttributeError(name)


__all__ = ["Transcriber"]
