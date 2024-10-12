import logging

from RealtimeTTS import CoquiEngine, SystemEngine, TextToAudioStream

from config import config

log = logging.getLogger(f"{config.name}.{__name__}")


class TTS:
    tts: TextToAudioStream

    def __init__(self):
        engine = SystemEngine()
        self.tts = TextToAudioStream(engine)

    def feed(self, text: str):
        # strip emojies but only emojis from text
        text = "".join(char for char in text if char.isprintable())

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
    # engine = CoquiEngine(local_models_path=join("obs_tools", "ttsmodels"), speed=1.3)

    return TTS()


# https://github.com/snakers4/silero-models?tab=readme-ov-file
