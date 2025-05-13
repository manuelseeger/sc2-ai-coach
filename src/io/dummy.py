from time import time

from src.contracts import TTSService


class TTSDummy(TTSService):
    def __init__(self):
        # Maintain a list of (text_length, start_time) for each feed
        self._speaking_queue = []

    def feed(self, text):
        # Add a new speaking event to the queue
        text_length = len(text)
        if text_length > 0:
            self._speaking_queue.append((text_length, time()))

    def stop(self):
        # Stop all speaking events
        self._speaking_queue.clear()

    def is_speaking(self) -> bool:
        # Remove finished speaking events
        now = time()
        new_queue = []
        for text_length, start_time in self._speaking_queue:
            duration = text_length / 20  # simulate normal speaking speed
            if now - start_time < duration:
                new_queue.append((text_length, start_time))
        self._speaking_queue = new_queue
        return len(self._speaking_queue) > 0
