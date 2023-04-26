import os
import openai
import argparse
import time
import pyttsx3
import speech_recognition as sr
import pymongo
from pymongo.server_api import ServerApi
import torch
import elevenlabs
import numpy as np
import whisper

elevenlabs.set_api_key(os.environ.get("ELEVEN_API_KEY"))

USE_11 = False

voiceengine = pyttsx3.init()
voices = voiceengine.getProperty("voices")
voiceengine.setProperty("voice", voices[3].id)

MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASS = os.environ.get("MONGO_PASS")


client = pymongo.MongoClient(
    "mongodb+srv://{}:{}@sc2.k2kgmgk.mongodb.net/?retryWrites=true&w=majority".format(
        MONGO_USER, MONGO_PASS
    ),
    server_api=ServerApi("1"),
)

db = client.SC2
mongo_replays = db.replays

openai.organization = os.getenv("OPENAI_API_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")

if torch.cuda.is_available():
    device = torch.device("cuda:0")
    print("GPU")
    print(torch.cuda.current_device())
    print(torch.cuda.device(0))
    print(torch.cuda.get_device_name(0))
else:
    device = torch.device("cpu")
    print("CPU")
audio_model = whisper.load_model("base.en").to(device)


def main():
    parser = argparse.ArgumentParser(description="Analyze replays")

    parser.add_argument("replays", nargs="+", help="Replays to analyze")
    parser.add_argument(
        "--deamonnize", "-d", action="store_true", help="Run as a daemon"
    )

    args = parser.parse_args()

    build_orders = ""
    opponent = "Driftoss"

    replays = replays_for_player(opponent)

    for replay in replays:
        build_orders += "Date: {}\n".format(replay["date"])
        build_orders += "Map: {}\n".format(replay["map_name"])
        build_orders += "Duration: {} seconds\n".format(replay["game_length"])
        build_orders += "Players:\n{}\n".format(
            "\n".join(
                ["{} ({})".format(p["name"], p["play_race"]) for p in replay["players"]]
            )
        )
        build_orders += "Winner: {}\n".format(
            [p for p in replay["players"] if p["result"] == "Win"][0]["name"]
        )

        build_orders += "Build Order ({}):\n".format(opponent)
        for player in replay["players"]:
            if player["name"] == opponent:
                for tick in player["build_order"]:
                    timestamp = time.strptime(tick["time"], "%M:%S")
                    if timestamp.tm_min < 7:
                        build_orders += tick["time"] + " " + tick["name"] + "\n"
        build_orders += "\n\n"

    conversation(opponent, build_orders)


def conversation(player, build_orders):
    r = sr.Recognizer()

    priming = """The player I might have recently played against is called "{opponent}".

Here are some recent games of me aganst {opponent} with the build orders played by {opponent}. Use these to answer follow up questions on this player's play style.

{bo}""".format(
        opponent=player, bo=build_orders
    )

    question = "Hey coach, can you please give me a quick rundown of the opening builds {opponent} did in recent games? Also, how many probes did he have at 5 minutes game time?".format(
        opponent=player
    )

    messages = [
        {
            "role": "system",
            "content": """You are my virtual coach for the strategy game StarCraft 2.

My name in StarCraft games is 'zatic'. You are given the name of an opponent player I might have played against.
If that is the case, you also get recent games and the build orders by that player from those games. Use this to answer questions on the games and the opponent.

Once you think our conversation is over, please wish me "good luck, have fun" """,
        },
        {
            "role": "user",
            "content": priming,
        },
    ]

    prompt = ""
    while True:
        with sr.Microphone() as source:
            print(">>>")
            audio = r.listen(source)
            prompt = transcribe(audio)
            print(prompt)

        if prompt.lower().startswith("stop"):
            break

        messages.append(
            {
                "role": "user",
                "content": prompt,
            },
        )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
        )
        messages.append(
            {"role": "assistant", "content": response["choices"][0]["message"].content}
        )
        print("<<<")
        print(response["choices"][0]["message"].content)

        say(text=response["choices"][0]["message"].content)


def transcribe(audio):
    audio_data = torch.from_numpy(
        np.frombuffer(audio.get_raw_data(), np.int16).flatten().astype(np.float32)
        / 32768.0
    )
    result = audio_model.transcribe(audio_data, language="english")
    return result["text"]


def say(text):
    if USE_11:
        audio = elevenlabs.generate(text=text, voice="Domi")
        elevenlabs.play(audio)
    else:
        voiceengine.say(text)
        voiceengine.runAndWait()


def replays_for_player(player):
    q = {"players": {"$elemMatch": {"name": player}}}
    replays = mongo_replays.find(q)
    return replays


if __name__ == "__main__":
    main()
