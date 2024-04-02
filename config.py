from pydantic import BaseModel
from typing import Dict, List, Type, Tuple
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    YamlConfigSettingsSource,
    PydanticBaseSettingsSource,
    EnvSettingsSource,
    DotEnvSettingsSource,
)
from typing import Annotated
from glob import glob
from pydantic.networks import UrlConstraints
from pydantic_core import MultiHostUrl, Url
from enum import Enum

# https://github.com/pydantic/pydantic/pull/7116
MongoSRVDsn = Annotated[MultiHostUrl, UrlConstraints(allowed_schemes=["mongodb+srv", "mongodb"])]


def sort_config_files(files):
    def key_func(file: str):
        return (not file.startswith("."), file.count("."))

    return sorted(files, key=key_func)


yaml_files = glob("config*.yml")
yaml_files = sort_config_files(yaml_files)

env_files = glob(".env*")
env_files = sort_config_files(env_files)
env_files.remove(".env.example")



class AudioMode(str, Enum):
    text = "text"
    voice_in = "in"
    voice_out = "out"
    full = "fullaudio"

class RecognizerConfig(BaseModel):
    energy_threshold: int = 400
    pause_threshold: float = 0.5
    phrase_threshold: float = 0.3
    non_speaking_duration: float = 0.2


class StudentConfig(BaseModel):
    name: str
    race: str
    sc2replaystats_map_url: Url
    emoji: str = ":man_technologist:"

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        yaml_file=yaml_files, env_file=env_files, env_prefix="AICOACH_", extra="ignore"
    )
    name: str = "AICoach"
    replay_folder: str
    instant_leave_max: int = 60
    deamon_polling_rate: int = 10

    audiomode: AudioMode = AudioMode.full
    microphone_index: int = 2
    oww_model: str = "hey_jarvis"
    oww_sensitivity: float = 0.7
    speech_recognition_model: str
    recognizer: RecognizerConfig = RecognizerConfig()
    wake_key: str = "ctrl+alt+w"

    student: StudentConfig

    openai_api_key: str
    openai_org_id: str
    assistant_id: str
    gpt_model: str = "gpt-3.5-turbo"

    obs_integration: bool = False
    screenshot: str = "obs/screenshots/_maploading.png"
    tessdata_dir: str = "C:\\Program Files\\Tesseract-OCR\\tessdata"

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

    db_name: str = "SC2"
    mongo_dsn: MongoSRVDsn

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: EnvSettingsSource,
        dotenv_settings: DotEnvSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            YamlConfigSettingsSource(settings_cls),
        )


config: Config = Config()
