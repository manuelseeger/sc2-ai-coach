from threading import Thread
from time import sleep
from typing import Callable, Dict, Generator
from uuid import uuid4

import tiktoken
from openai.types.beta.threads import Message, Text, TextContentBlock
from typing_extensions import override

from .aicoach import AICoach

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
        self.set_data(data)

    def set_data(self, data):
        self._data = data
        self._responses = iter(self._data)

    # public
    @override
    def create_thread(self, message=None):
        self.current_thread_id = uuid4().hex
        sleep(0.5)
        pass

    @override
    def stream_thread(self) -> Generator[str, None, None]:
        sleep(1)
        for token in self.generate_stream():
            yield token

    @override
    def chat(self, text) -> Generator[str, None, None]:
        sleep(1)
        if text == "done":
            yield "Good luck, "
            yield "have fun"
            return
        for token in self.generate_stream():
            yield token

    @override
    def get_conversation(self) -> list[Message]:
        return [
            Message(
                content=[
                    TextContentBlock(text=Text(value=msg, annotations=[]), type="text")
                ],
                id=uuid4().hex,
                created_at=0,
                file_ids=[],
                object="thread.message",
                role="assistant",
                status="completed",
                thread_id=self.current_thread_id,
            )
            for msg in self._data
        ]

    def generate_stream(self):
        msg = next(self._responses, "I'm sorry, I don't have anything more to say")
        tokens = encoding.encode(msg)
        for token in tokens:
            sleep(0.05)
            yield encoding.decode([token])
