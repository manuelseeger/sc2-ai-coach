from os.path import join

from RealtimeTTS import CoquiEngine, SystemEngine, TextToAudioStream


class TTS:
    tts: TextToAudioStream

    def __init__(self):
        engine = SystemEngine()
        self.tts = TextToAudioStream(engine)

    def feed(self, text: str):
        # strip emojies but only emojis from text

        self.tts.feed(text)
        if not self.tts.is_playing():
            self.tts.play_async(
                buffer_threshold_seconds=2.8, fast_sentence_fragment=True
            )


def make_tts_stream():
    # engine = CoquiEngine(local_models_path=join("obs_tools", "ttsmodels"), speed=1.3)

    return TTS()


# https://github.com/snakers4/silero-models?tab=readme-ov-file
