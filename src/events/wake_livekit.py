import logging
import threading
import time
from collections import deque

import numpy as np
import pyaudio
from livekit.wakeword import WakeWordModel

from log import DEFAULT_LOGGER_NAME
from shared import signal_queue
from src.events import WakeEvent
from src.runtime.settings import Config, get_config

log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")

SAMPLE_RATE = 16000
FRAME_SAMPLES = 1280  # 80ms per frame
CHUNK_SECONDS = 2.0
# Number of 80ms frames that fill a ~2-second chunk (25 frames).
CHUNK_FRAMES = int(CHUNK_SECONDS * SAMPLE_RATE / FRAME_SAMPLES)


class WakeWordListener(threading.Thread):
    def __init__(self, *, settings: Config | None = None):
        super().__init__()
        self.settings = settings or get_config()
        self.daemon = True
        self._stop_event = threading.Event()
        self.model = WakeWordModel(models=[self.settings.wakeword.model_path])
        self.threshold = self.settings.wakeword.threshold
        self.debounce = 2.0

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):

        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=FRAME_SAMPLES,
            input_device_index=self.settings.microphone_index,
        )
        log.debug(
            "Wake word listener started on device %s", self.settings.microphone_index
        )

        frame_buffer: deque[np.ndarray] = deque(maxlen=CHUNK_FRAMES)
        last_detection_time = 0.0

        try:
            while not self.stopped():
                data = stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                frame = np.frombuffer(data, dtype=np.int16)
                frame_buffer.append(frame)

                # Wait until the buffer holds a full ~2-second chunk.
                if len(frame_buffer) < CHUNK_FRAMES:
                    continue

                chunk = np.concatenate(list(frame_buffer))
                scores = self.model.predict(chunk)

                now = time.monotonic()
                for name, score in scores.items():
                    if (
                        score >= self.threshold
                        and now - last_detection_time >= self.debounce
                    ):
                        last_detection_time = now
                        frame_buffer.clear()
                        self.on_detection(name, score)
                        break
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    def on_detection(self, name: str, confidence: float) -> None:
        log.info("Detected wake word %s (%.2f)", name, confidence)
        signal_queue.put(WakeEvent(awake=True))
