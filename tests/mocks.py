from rich import print


class MicMock:
    def listen(self):
        return None

    def say(self, text):
        print(text)


class TTSMock:
    def feed(self, text):
        print(text)


class TranscriberMock:
    _data: list[str] = None

    def __init__(self, data: list[str] = None) -> None:
        self._data = data

    def transcribe(self, audio):
        return self._data.pop(0)
