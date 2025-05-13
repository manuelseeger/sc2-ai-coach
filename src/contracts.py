from abc import ABC, abstractmethod


class TranscriberService(ABC):
    @abstractmethod
    def transcribe(self, audio_file: str) -> str:
        pass


class MicrophoneService(ABC):
    @abstractmethod
    def listen(self, duration: int) -> str:
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
