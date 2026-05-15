from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from speech_recognition.audio import AudioData
else:
    AudioData = Any


class TranscriberService(Protocol):
    def transcribe(self, audio: AudioData) -> str: ...


class MicrophoneService(Protocol):
    def listen(self) -> AudioData | None: ...


class TTSService(Protocol):
    def feed(self, text: str) -> None: ...

    def stop(self) -> None: ...

    def is_speaking(self) -> bool: ...


class LiveEventListener(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def join(self) -> None: ...
