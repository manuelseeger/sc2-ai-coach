import sys
import pyttsx3


def init_engine():
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    engine.setProperty("voice", voices[3].id if len(voices) > 3 else voices[0].id)
    return engine


def say(s):
    engine.say(s)
    engine.runAndWait()  # In here the program will wait as if is in main file


if __name__ == "__main__":
    if len(sys.argv) > 1:
        engine = init_engine()

        say(str(sys.argv[1]))
    else:
        print("Usage: python3 mic.py <text>")
