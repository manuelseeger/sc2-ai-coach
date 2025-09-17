import logging
import threading
from datetime import datetime
from pathlib import Path
from time import sleep

import numpy as np
import pvporcupine
import pyaudio

from config import config
from shared import signal_queue
from src.events import WakeEvent

log = logging.getLogger(f"{config.name}.{__name__}")

# Initialize Porcupine with the custom keyword file
keyword_path = str(
    Path(__file__).parent.parent.parent
    / "external"
    / "porcupine"
    / "hey-coach_en_windows_v3_0_0.ppn"
)
access_key = config.wakeword.porcupine_accesskey

if not access_key:
    raise ValueError(
        "Porcupine access key must be provided in config.wakeword.porcupine_accesskey"
    )

if not Path(keyword_path).exists():
    raise FileNotFoundError(f"Porcupine keyword file not found: {keyword_path}")

porcupine = pvporcupine.create(access_key=access_key, keyword_paths=[keyword_path])

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = porcupine.sample_rate
CHUNK = porcupine.frame_length
MIC_INDEX = 2
audio = pyaudio.PyAudio()
mic_stream = audio.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK,
    input_device_index=MIC_INDEX,
)


class WakeWordListener(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        try:
            self.listen_for_wake_word()
        finally:
            if porcupine:
                porcupine.delete()

    def listen_for_wake_word(self):
        log.debug("Starting porcupine wakeword listener")
        last_score_timestamp = datetime.now()

        while True:
            if self.stopped():
                log.debug("Stopping porcupine wakeword listener")
                break

            audio_frame = np.frombuffer(mic_stream.read(CHUNK), dtype=np.int16)

            keyword_index = porcupine.process(audio_frame.tolist())

            if keyword_index >= 0:
                if (datetime.now() - last_score_timestamp).seconds > 5:
                    last_score_timestamp = datetime.now()
                    log.info(
                        f"Porcupine detected wake word 'hey coach' (index: {keyword_index})"
                    )
                    signal_queue.put(WakeEvent(awake=True))
                    sleep(5)
