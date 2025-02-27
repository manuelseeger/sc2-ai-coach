import pytest

from src.io.mic import Microphone
from src.io.transcribe import Transcriber
from src.io.tts import make_tts_stream


def test_voice_input():
    mic = Microphone()

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
    tts = make_tts_stream()
    tts.feed(text)


def test_transcribe():
    mic = Microphone()
    transcriber = Transcriber()

    audio = mic.listen()

    text = transcriber.transcribe(audio)

    assert text != ""
