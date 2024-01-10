from pydantic import BaseModel
from typing import Dict, List
from pydantic_yaml import parse_yaml_raw_as


class RecognizerConfig(BaseModel):
    energy_threshold: int = 400
    pause_threshold: float = 0.5
    phrase_threshold: float = 0.3
    non_speaking_duration: float = 0.2


class StudentConfig(BaseModel):
    name: str
    race: str
    sc2replaystats_map_url: str

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


class Config(BaseModel):
    name: str = "AICoach"
    replay_folder: str
    instant_leave_max: int = 60
    deamon_polling_rate: int = 10

    microphone_index: int = 2

    oww_model: str = "hey_jarvis"

    oww_sensitivity: float = 0.7

    student: StudentConfig

    gpt_model: str = "gpt-3.5-turbo"

    speech_recognition_model: str

    screenshot: str = "obs/screenshots/_maploading.png"

    recognizer: RecognizerConfig = RecognizerConfig()

    season: int = 57

    ladder_maps: List[str] = [
        "hecate le",
        "oceanborn le",
        "solaris le",
        "hard lead le",
        "radhuset station le",
        "site delta le",
        "equilibrium le",
        "goldenaura le",
        "alcyone le",
    ]

    default_projection: Dict[str, int] = {
        "_id": 1,
        "date": 1,
        "game_length": 1,
        "map_name": 1,
        "players.avg_apm": 1,
        "players.highest_league": 1,
        "players.name": 1,
        "players.messages": 1,
        "players.pick_race": 1,
        "players.pid": 1,
        "players.play_race": 1,
        "players.result": 1,
        "players.scaled_rating": 1,
        "players.stats": 1,
        "players.toon_handle": 1,
        "players.build_order.time": 1,
        "players.build_order.name": 1,
        "players.build_order.supply": 1,
        "players.build_order.is_chronoboosted": 1,
        "real_length": 1,
        "stats": 1,
        "unix_timestamp": 1,
    }


with open("config.yml") as f:
    config_yml = f.read()

config: Config = parse_yaml_raw_as(Config, config_yml)
