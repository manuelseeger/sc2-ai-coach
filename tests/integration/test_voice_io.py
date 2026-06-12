import pytest
from rich import print

pytest.importorskip("RealtimeTTS")
pytest.importorskip("speech_recognition")
pytest.importorskip("soundfile")

from iosvc import get_transcriber_class
from iosvc.mic import Microphone
from iosvc.tts import make_tts_stream
from tests.conftest import load_test_settings

settings = load_test_settings()


def test_voice_input():
    mic = Microphone(
        device_index=settings.microphone_index,
        recognizer_config=settings.recognizer,
    )

    audio = mic.listen()  # noqa: F841

    assert True


@pytest.mark.parametrize(
    "text",
    [
        "Hello, world!",
        """Congrats on the win, zatic! 🎉 Beating WaCKii with that solid performance is awesome.

Would you like to go through the replay together? Feel free to ask me anything about the replay or WaCKii's playstyle. Let's dig into those details!
""",
        """Alright, zatic, here’s the scoop on your past games against aikrash:

1. **Replay from September 1, 2024, on Post-Youth LE**: aikrash used a standard Zerg build with a focus on Zerglings and Banelings transition into Roaches, but you outplayed him and secured the win.

2. **Replay from August 12, 2024, on Amphion LE**: aikrash went for a Roach-based strategy with a Lair tech and some mid-game aggression, but again, you handled it like a champ and took the victory. He didn't GG in this one either and complained about cheats at the end 🤷‍♂️.

You haven't played aikrash on Alcyone LE before, so he might try something different this time. Any questions on these games?""",
    ],
)
def test_voice_output(text):
    tts = make_tts_stream(tts_config=settings.tts)
    tts.feed(text)


def test_transcribe():
    mic = Microphone(
        device_index=settings.microphone_index,
        recognizer_config=settings.recognizer,
    )
    transcriber_class = get_transcriber_class(settings.transcriber_backend)

    if settings.transcriber_backend.value == "xai":
        transcriber = transcriber_class(
            api_key=settings.xai_api_key,
            language=settings.xai_stt_language,
        )
    elif settings.transcriber_backend.value == "whisper":
        transcriber = transcriber_class(model_id=settings.speech_recognition_model)
    else:
        transcriber = transcriber_class()

    audio = mic.listen()

    text = transcriber.transcribe(audio)

    print(text)

    assert text != ""
