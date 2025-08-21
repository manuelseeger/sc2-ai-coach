from abc import ABC, abstractmethod

from speech_recognition.audio import AudioData


class TranscriberService(ABC):
    @abstractmethod
    def transcribe(self, audio: AudioData) -> str:
        pass


class MicrophoneService(ABC):
    @abstractmethod
    def listen(self) -> AudioData | None:
        pass


class TTSService(ABC):
    @abstractmethod
    def feed(self, text: str) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def is_speaking(self) -> bool:
        pass
