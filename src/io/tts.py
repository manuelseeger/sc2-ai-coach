import logging
import re

from RealtimeTTS import KokoroEngine, SystemEngine, TextToAudioStream

from config import config

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


def strip_markdown(md_text: str):
    # strip emojies
    text = "".join(char for char in md_text if char.isprintable())
    # Remove links
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Remove bold/italic (**text**, *text*, __text__, _text_)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)

    # Remove headings (#, ##, ###, etc.)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

    # Remove inline code (`code`)
    text = re.sub(r"`(.*?)`", r"\1", text)

    # Remove images while ensuring no extra spaces remain
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(
        r"\s*!\[.*?\]\(.*?\)\s*", " ", text
    )  # Extra safeguard for inline images

    # Remove unordered list markers (-, *, +)
    text = re.sub(r"^\s*[-*+]\s*", "", text, flags=re.MULTILINE)

    # Remove ordered list markers (1., 2., 3.)
    text = re.sub(r"^\s*\d+\.\s*", "", text, flags=re.MULTILINE)

    return text
