from src.runtime.settings import TranscriberBackend


def get_transcriber_class(transcriber_backend: TranscriberBackend):
    if transcriber_backend == TranscriberBackend.canary_qwen:
        from src.io.transcribe_qwen import QwenTranscriberService

        return QwenTranscriberService
    if transcriber_backend == TranscriberBackend.xai:
        from src.io.transcribe_xai import XAITranscriberService

        return XAITranscriberService

    from src.io.transcribe_whisper import Transcriber

    return Transcriber


__all__ = ["get_transcriber_class"]
