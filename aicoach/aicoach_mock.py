import random
from threading import Thread
from time import sleep
from typing import Callable, Dict, Generator, Type
from uuid import uuid4

import tiktoken
from openai.types.beta.threads import Message, Text, TextContentBlock
from openai.types.beta.threads.run import Usage
from typing_extensions import override

from .aicoach import AICoach, TBaseModel

data = [
    "The current supply count is not part of the game information provided. I can give insights based on replays on record but not from live games or current replays in progress. Would you like me to look up a recent replay instead?",
    "In the most recent replay involving zatic on the map Goldenaura LE, zatic played Zerg and won the game with a final supply count of 195.",
]
data = [
    {
        "role": "assistant",
        "text": "Congratulations on the win, zatic!\n\nIf you'd like, we can go through the replay together. Let me know if you have any questions about the replay or your opponent, RichieBravo.",
    },
    {
        "role": "user",
        "text": " Thank you.",
    },
    {
        "role": "assistant",
        "text": "Good luck, have fun.",
    },
    {
        "role": "assistant",
        "text": "In the game on Alcyone LE, you, zatic, executed a Zergling-Baneling focused aggressive strategy against RichieBravo, with an early Spawning Pool followed by quick Zergling pressure. You kept up continuous Zergling production and added a Baneling Nest to bolster your aggressive stance. RichieBravo opted for an earlier Hatchery before Spawning Pool, transitioning into Zerglings and a later Baneling Nest, aiming for a more economic opening. Your relentless aggression with Zerglings and Banelings, complemented by timely Evolution Chambers for upgrades, allowed you to maintain pressure and control the pace of the game. Despite initial economic disadvantage due to the quick tech, your aggression paid off, leading to a win with heavy Zergling-Baneling plays and superior APM.",
    },
    {
        "role": "assistant",
        "text": ", ".join(
            [
                "Spawning Pool first",
                "Zergling-Baneling pressure",
                "early Evolution Chambers",
                "Zerg Melee Weapons Level 1",
                "Zerg Ground Armor Level 1",
                "Metabolic Boost",
                "Baneling Nest",
                "APM advantage",
            ]
        ),
    },
]

encoding = tiktoken.get_encoding("cl100k_base")


class AICoachMock(AICoach):
    thread_id: str = None
    threads: Dict[str, Thread] = {}
    thread: Thread = None

    _usages: list[Usage] = []

    functions: Dict[str, Callable] = {}

    def __init__(self):
        self._init_functions()
        self.set_data(data)

    def set_data(self, data):
        self._data = data
        self._responses = iter([d for d in self._data if d.get("role") == "assistant"])

    @override
    def get_thread_usage(self, thread_id: str) -> Usage:
        thread_usage = Usage(completion_tokens=0, prompt_tokens=0, total_tokens=0)
        for usage in self._usages:
            thread_usage.completion_tokens += usage.completion_tokens
            thread_usage.prompt_tokens += usage.prompt_tokens
            thread_usage.total_tokens += usage.total_tokens
        return thread_usage

    @override
    def create_thread(self, message=None):
        self.thread_id = uuid4().hex
        sleep(0.5)
        return self.thread_id

    @override
    def stream_thread(self) -> Generator[str, None, None]:
        sleep(1)
        for token in self.generate_stream():
            yield token

    @override
    def chat(self, text: str) -> Generator[str, None, None]:
        sleep(1)
        if text == "done" or "thank you" in text.lower():
            yield "Good luck, "
            yield "have fun"
            return
        for token in self.generate_stream():
            yield token

    @override
    def get_structured_response(self, message, schema: type[TBaseModel]) -> TBaseModel:
        raise NotImplementedError

    @override
    def get_conversation(self) -> list[Message]:
        return [
            Message(
                content=[
                    TextContentBlock(
                        text=Text(value=msg.get("text"), annotations=[]), type="text"
                    )
                ],
                id=uuid4().hex,
                created_at=0,
                file_ids=[],
                object="thread.message",
                role=msg.get("role"),
                status="completed",
                thread_id=self.thread_id,
            )
            for msg in self._data
        ]

    def generate_stream(self):
        msg = next(
            self._responses, {"text": "I'm sorry, I don't have anything more to say"}
        )
        tokens = encoding.encode(msg.get("text"))
        for token in tokens:
            sleep(0.03)
            yield encoding.decode([token])
        self._add_usage()

    def _add_usage(self):
        completion_tokens = random.randint(10, 200)
        prompt_tokens = random.randint(2400, 2700)
        total_tokens = completion_tokens + prompt_tokens
        self._usages.append(
            Usage(
                completion_tokens=completion_tokens,
                prompt_tokens=prompt_tokens,
                total_tokens=total_tokens,
            )
        )
