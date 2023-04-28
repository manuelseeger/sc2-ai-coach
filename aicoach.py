import os
import openai
import argparse
import time
import pyttsx3
import pymongo
from pymongo.server_api import ServerApi
import torch
import elevenlabs
import numpy as np
import whisper
import speech_recognition as sr
import soundfile as sf
import io
from Levenshtein import distance as levenshtein


def main():
    parser = argparse.ArgumentParser(description="Analyze replays")

    parser.add_argument("replays", nargs="+", help="Replays to analyze")
    parser.add_argument(
        "--deamonnize", "-d", action="store_true", help="Run as a daemon"
    )

    args = parser.parse_args()

    coach = AICoach()

    coach.init()

    opponent = "Driftoss"

    build_orders = coach.get_replays(opponent)

    coach.start_conversation(opponent, build_orders)


class AICoach:
    def init(self, harstem=False):
        elevenlabs.set_api_key(os.environ.get("ELEVEN_API_KEY"))

        self.USE_11 = harstem

        self.voiceengine = pyttsx3.init()
        voices = self.voiceengine.getProperty("voices")
        self.voiceengine.setProperty("voice", voices[3].id)

        client = pymongo.MongoClient(
            "mongodb+srv://{}:{}@sc2.k2kgmgk.mongodb.net/?retryWrites=true&w=majority".format(
                os.environ.get("MONGO_USER"), os.environ.get("MONGO_PASS")
            ),
            server_api=ServerApi("1"),
        )

        db = client.SC2
        self.mongo_replays = db.replays

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
        self.audio_model = whisper.load_model("base.en").to(device)

        self.recognizer = sr.Recognizer()

        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)

    def get_replays(self, opponent):
        build_orders = ""

        replays = self.replays_for_player(opponent)

        for replay in replays:
            build_orders += "Date: {}\n".format(replay["date"])
            build_orders += "Map: {}\n".format(replay["map_name"])
            build_orders += "Duration: {} seconds\n".format(replay["game_length"])
            build_orders += "Players:\n{}\n".format(
                "\n".join(
                    [
                        "{} ({})".format(p["name"], p["play_race"])
                        for p in replay["players"]
                    ]
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

        return build_orders

    def start_conversation(self, player, build_orders):
        priming = """The player I might have recently played against is called "{opponent}".

    Here are some recent games of me aganst {opponent} with the build orders played by {opponent}. Use these to answer follow up questions on this player's play style.

    {bo}""".format(
            opponent=player, bo=build_orders
        )

        if self.USE_11:
            namephrase = "Your name is Harstem."
        else:
            namephrase = ""

        self.messages = [
            {
                "role": "system",
                "content": """You are my virtual coach for the strategy game StarCraft 2. {namephrase}

    My name in StarCraft games is 'zatic'. You are given the name of an opponent player I might have played against.
    If that is the case, you also get recent games and the build orders by that player from those games. Use this to answer questions on the games and the opponent.

    When asked about build orders, please always try to summarize them to the essentials, and don't just return the full build order.

    Once you think our conversation is over, please end the conversation with the exact phrase "good luck, have fun". Make sure the conversation ends on that phrase exactly. """.format(
                    namephrase=namephrase
                ),
            },
            {
                "role": "user",
                "content": priming,
            },
        ]

        while self.chat():
            pass

    def chat(self):
        with sr.Microphone() as source:
            print(">>>")
            audio = self.recognizer.listen(source)
            prompt = self.transcribe(audio)
            if self.is_silence(prompt):
                return True
            print(prompt)

        if self.is_stop_command(prompt):
            return False

        self.messages.append(
            {
                "role": "user",
                "content": prompt,
            },
        )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=self.messages,
        )
        self.messages.append(
            {
                "role": "assistant",
                "content": response["choices"][0]["message"].content,
            }
        )
        print("<<<")
        print(response["choices"][0]["message"].content)
        self.say(text=response["choices"][0]["message"].content)

        if self.is_goodbye(response["choices"][0]["message"].content):
            return False
        return True

    def is_goodbye(self, response):
        if levenshtein(response[-20:].lower().strip(), "good luck, have fun") < 8:
            return True
        else:
            return False

    def is_stop_command(self, prompt):
        return prompt.lower().strip().startswith("stop")

    def is_silence(self, prompt):
        return len(prompt.strip()) < 10

    def transcribe(self, audio):
        wav_bytes = audio.get_wav_data(convert_rate=16000)
        wav_stream = io.BytesIO(wav_bytes)
        audio_array, sampling_rate = sf.read(wav_stream)
        audio_array = audio_array.astype(np.float32)

        result = self.audio_model.transcribe(
            audio_array,
            language="en",
            fp16=torch.cuda.is_available(),
        )
        return result["text"]

    def say(self, text):
        if self.USE_11:
            voices = elevenlabs.voices()
            voice = None
            for v in voices:
                if v.name == "Coach Harstem":
                    voice = v
            if voice is None:
                raise Exception("Voice not found")
            voice.settings = elevenlabs.VoiceSettings(
                stability=0.25, similarity_boost=0.75
            )
            audio = elevenlabs.generate(text=text, voice=voice)
            elevenlabs.play(audio)
        else:
            self.voiceengine.say(text)
            self.voiceengine.runAndWait()

    def replays_for_player(self, player):
        q = {"players": {"$elemMatch": {"name": player}}}
        replays = self.mongo_replays.find(q)
        return replays


if __name__ == "__main__":
    main()
