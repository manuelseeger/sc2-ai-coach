from runtime.settings import TranscriberBackend


def get_transcriber_class(transcriber_backend: TranscriberBackend):
    if transcriber_backend == TranscriberBackend.canary_qwen:
        from iosvc.transcribe_qwen import QwenTranscriberService

        return QwenTranscriberService
    if transcriber_backend == TranscriberBackend.xai:
        from iosvc.transcribe_xai import XAITranscriberService

        return XAITranscriberService

    from iosvc.transcribe_whisper import Transcriber

    return Transcriber


__all__ = ["get_transcriber_class"]
