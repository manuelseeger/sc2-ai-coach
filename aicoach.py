import os
import openai
import time
import pyttsx3
import torch
import elevenlabs
import numpy as np
import whisper
import speech_recognition as sr
import soundfile as sf
import io
from Levenshtein import distance as levenshtein
from replaydb import ReplayDB
from pyaudio import PyAudio


class AICoach:
    def init(self, config, log=None, harstem=False, debug=False):
        elevenlabs.set_api_key(os.environ.get("ELEVEN_API_KEY"))

        self.USE_11 = harstem
        self.DEBUG = debug

        if log is not None:
            self.log = log
        else:
            import logging

            self.log = logging.getLogger(__name__)

        self.voiceengine = pyttsx3.init()
        voices = self.voiceengine.getProperty("voices")
        self.voiceengine.setProperty("voice", voices[3].id)

        self.replay_db = ReplayDB(config=config, debug=debug)

        openai.organization = os.getenv("OPENAI_API_ID")
        openai.api_key = os.getenv("OPENAI_API_KEY")

        if torch.cuda.is_available():
            device = torch.device("cuda:0")
            self.log.info("GPU")
            self.log.info(torch.cuda.current_device())
            self.log.info(torch.cuda.device(0))
            self.log.info(torch.cuda.get_device_name(0))
        else:
            device = torch.device("cpu")
            self.log.info("CPU")
        self.audio_model = whisper.load_model("base.en").to(device)

        audio = PyAudio()

        if not config.microphone_index:
            microphone_index = 0
            for i in range(0, audio.get_device_count() - 1):
                device = audio.get_device_info_by_index(i)

                # if device["name"] == "Microphone (2- Shure MV7)":
                if device["name"] == "Microphone (NVIDIA Broadcast)":
                    microphone_index = i
                    log.info(f"Found microphone { device['name'] }")
                    break
        else:
            microphone_index = config.microphone_index

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = config.recognizer.energy_threshold
        self.recognizer.pause_threshold = config.recognizer.pause_threshold
        self.recognizer.phrase_threshold = config.recognizer.phrase_threshold
        self.recognizer.non_speaking_duration = config.recognizer.non_speaking_duration

        self.microphone = sr.Microphone(device_index=microphone_index)

        # with self.microphone as source:
        #    self.recognizer.adjust_for_ambient_noise(source)

    def get_replays(self, opponent):
        build_orders = []

        replays = self.replay_db.replays_for_player(opponent)

        for replay in replays:
            build = "Date: {}\n".format(replay["date"])
            build += "Map: {}\n".format(replay["map_name"])
            build += "Duration: {} seconds\n".format(replay["game_length"])
            build += "Players:\n{}\n".format(
                "\n".join(
                    [
                        "{} ({})".format(p["name"], p["play_race"])
                        for p in replay["players"]
                    ]
                )
            )
            build += "Winner: {}\n".format(
                [p for p in replay["players"] if p["result"] == "Win"][0]["name"]
            )
            if self.DEBUG:
                print(build)

            build += "Build Order ({}):\n".format(opponent)
            for player in replay["players"]:
                if player["name"] == opponent:
                    for tick in player["build_order"]:
                        timestamp = time.strptime(tick["time"], "%M:%S")
                        if timestamp.tm_min < 7:
                            build += tick["time"] + " " + tick["name"] + "\n"
            build += "\n\n"
            build_orders.append(build)

        return build_orders

    def start_conversation(self, player, build_orders):
        priming = (
            f"""The player I might have recently played against is called "{player}"."""
        )

        if len(build_orders) > 0:
            priming += f"""

Here are some recent games of me aganst {player} with the build orders played by {player}. Use these to answer follow up questions on this player's play style.

{ "".join(build_orders) }"""
        else:
            priming += f"""

There are no recent games against {player} in my database. When asked about it, just tell me that."""

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
        with self.microphone as source:
            print(">>>")
            audio = self.recognizer.listen(source)
            self.log.info("Got voice input")
            prompt = self.transcribe(audio)
            self.log.info("Transcribed voice input")
            if self.is_silence(prompt):
                return True
            print(prompt)

        if self.is_stop_command(prompt):
            print("Stop")
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
            print("Goodbye")
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
