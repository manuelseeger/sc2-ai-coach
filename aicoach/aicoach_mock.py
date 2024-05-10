from threading import Thread
from typing import Dict, Callable
from .aicoach import AICoach
from typing_extensions import override
from typing import Dict, Callable, Generator
import tiktoken
from time import sleep
from uuid import uuid4

data = [
    "The current supply count is not part of the game information provided. I can give insights based on replays on record but not from live games or current replays in progress. Would you like me to look up a recent replay instead?",
    "In the most recent replay involving zatic on the map Goldenaura LE, zatic played Zerg and won the game with a final supply count of 195.",
]

encoding = tiktoken.get_encoding("cl100k_base")


class AICoachMock(AICoach):
    current_thread_id: str = None
    threads: Dict[str, Thread] = {}
    thread: Thread = None

    functions: Dict[str, Callable] = {}

    def __init__(self):
        self._init_functions()

        # mock data in reverse
        self._data = data[::-1]

    # public
    @override
    def create_thread(self, message=None):
        self.current_thread_id = uuid4().hex
        sleep(0.5)
        pass

    @override
    def stream_thread(self) -> Generator[str, None, None]:
        sleep(1)
        yield ""

    @override
    def chat(self, text) -> Generator[str, None, None]:
        sleep(1)
        msg = self._data.pop()
        tokens = encoding.encode(msg)
        for token in tokens:
            sleep(0.05)
            yield encoding.decode([token])
