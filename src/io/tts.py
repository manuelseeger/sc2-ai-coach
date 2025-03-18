import logging

from RealtimeTTS import KokoroEngine, SystemEngine, TextToAudioStream

from config import config
from src.util import strip_markdown

log = logging.getLogger(f"{config.name}.{__name__}")


class TTS:
    tts: TextToAudioStream

    def __init__(self, engine=None):
        if engine is None:
            engine = SystemEngine()
        self.tts = TextToAudioStream(engine)

    def feed(self, text: str):
        text = strip_markdown(text)

        # log.debug(f"Feeding TTS: {text}")

        try:
            self.tts.feed(text)
            if not self.tts.is_playing():
                self.tts.play_async(
                    buffer_threshold_seconds=2.8, fast_sentence_fragment=True
                )
        except RecursionError as e:
            log.warning("RecursionError in TTS")
            log.debug(e)
            pass

    def stop(self):
        self.tts.stop()


def make_tts_stream():
    engine = None
    if config.tts.engine == "kokoro":
        engine = KokoroEngine()
        if config.tts.voice:
            engine.set_voice(config.tts.voice)

    if config.tts.engine == "system":
        engine = SystemEngine()

    return TTS(engine=engine)


def init_tts():
    from RealtimeTTS import KokoroEngine, TextToAudioStream

    engine = KokoroEngine()
    engine.set_voice(config.tts.voice)
    text = "Warm up"
    TextToAudioStream(engine).feed(text).play(muted=True)
    text = "Hello, this is your friendly AI coach getting ready"
    TextToAudioStream(engine).feed([text]).play(log_synthesized_text=True)

    engine.shutdown()
