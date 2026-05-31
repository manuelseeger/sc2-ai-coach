import contextlib
import logging
import threading
import time
from collections import deque

import numpy as np
import onnxruntime as ort
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
# Run inference once per ~400ms (every 5th frame) rather than on every frame.
# The model is stateless and scores a full ~2s window per call, so predicting
# on every 80ms frame means ~12.5 redundant 2s inferences/sec -> high CPU.
HOP_FRAMES = 5


@contextlib.contextmanager
def _lean_onnx_sessions():
    """Make WakeWordModel build its ONNX sessions single-threaded and non-spinning.

    The models are tiny but get run ~18x per predict. ORT defaults to one
    intra-op thread per physical core plus a busy spin-wait between ops, which
    burns CPU out of proportion to the actual work. The library creates its
    sessions internally with default options, so we temporarily wrap the
    InferenceSession constructor to inject leaner SessionOptions.
    """
    original = ort.InferenceSession

    def patched(*args, **kwargs):
        if "sess_options" not in kwargs:
            so = ort.SessionOptions()
            so.intra_op_num_threads = 1
            so.inter_op_num_threads = 1
            # Don't busy-wait between ops; release the CPU instead.
            so.add_session_config_entry("session.intra_op.allow_spinning", "0")
            kwargs["sess_options"] = so
        return original(*args, **kwargs)

    ort.InferenceSession = patched
    try:
        yield
    finally:
        ort.InferenceSession = original


class WakeWordListener(threading.Thread):
    def __init__(self, *, settings: Config | None = None):
        super().__init__()
        self.settings = settings or get_config()
        self.daemon = True
        self._stop_event = threading.Event()
        with _lean_onnx_sessions():
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
        frames_since_predict = 0

        try:
            while not self.stopped():
                data = stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                frame = np.frombuffer(data, dtype=np.int16)
                frame_buffer.append(frame)
                frames_since_predict += 1

                # Wait until the buffer holds a full ~2-second chunk, then only
                # run inference on a hop (every HOP_FRAMES frames) to keep CPU low.
                if len(frame_buffer) < CHUNK_FRAMES:
                    continue
                if frames_since_predict < HOP_FRAMES:
                    continue
                frames_since_predict = 0

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
