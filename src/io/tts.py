import logging
from typing import TYPE_CHECKING

from RealtimeTTS import SystemEngine, TextToAudioStream
from RealtimeTTS.engines.kokoro_engine import KokoroEngine

from src.contracts import TTSService
from src.util import strip_markdown

if TYPE_CHECKING:
    from src.runtime.settings import TTSConfig

from log import DEFAULT_LOGGER_NAME
log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")


class TTS(TTSService):
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

    def is_speaking(self):
        # https://github.com/KoljaB/RealtimeTTS/issues/320
        return self.tts.stream_running and self.tts.is_playing_flag
        # return self.tts.is_playing()


def make_tts_stream(*, tts_config: "TTSConfig") -> TTS:
    engine = None
    if tts_config.engine == "kokoro":
        engine = KokoroEngine()
        if tts_config.voice:
            engine.set_voice(tts_config.voice)
        if tts_config.speed:
            engine.set_speed(tts_config.speed)

    if tts_config.engine == "system":
        engine = SystemEngine()

    return TTS(engine=engine)


def init_tts(tts_config: "TTSConfig"):
    from RealtimeTTS import KokoroEngine, TextToAudioStream

    engine = KokoroEngine()
    if tts_config.voice:
        engine.set_voice(tts_config.voice)
    text = "Warm up"
    TextToAudioStream(engine).feed(text).play(muted=True)
    text = "Hello, this is your friendly AI coach getting ready"
    TextToAudioStream(engine).feed(text).play(log_synthesized_text=True)

    engine.shutdown()
