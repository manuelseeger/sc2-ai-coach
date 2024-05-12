from os.path import join

from RealtimeTTS import CoquiEngine, SystemEngine, TextToAudioStream


def make_tts_stream():
    # engine = CoquiEngine(local_models_path=join("obs_tools", "ttsmodels"), speed=1.3)
    engine = SystemEngine()
    tts = TextToAudioStream(engine)
    return tts


# https://github.com/snakers4/silero-models?tab=readme-ov-file
