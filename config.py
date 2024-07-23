from enum import Enum
from glob import glob
from typing import Annotated, Dict, List, Tuple, Type

from pydantic import BaseModel
from pydantic.networks import UrlConstraints
from pydantic_core import MultiHostUrl, Url
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

# https://github.com/pydantic/pydantic/pull/7116
MongoSRVDsn = Annotated[
    MultiHostUrl, UrlConstraints(allowed_schemes=["mongodb+srv", "mongodb"])
]


def sort_config_files(files):
    def key_func(filename: str):
        return (not filename.startswith("."), filename.count("."))

    return sorted(files, key=key_func)


yaml_files = glob("config*.yml")
yaml_files = sort_config_files(yaml_files)

env_files = glob(".env*")
env_files = sort_config_files(env_files)
env_files.remove(".env.example")


class CoachEvent(str, Enum):
    wake = "wake"
    game_start = "game_start"
    new_replay = "new_replay"


class AIBackend(str, Enum):
    openai = "OpenAI"
    mocked = "Mocked"


class AudioMode(str, Enum):
    text = "text"
    voice_in = "in"
    voice_out = "out"
    full = "full"


class RecognizerConfig(BaseModel):
    energy_threshold: int
    pause_threshold: float
    phrase_threshold: float
    non_speaking_duration: float
    speech_threshold: float


class StudentConfig(BaseModel):
    name: str
    race: str
    sc2replaystats_map_url: Url | None = None
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
    instant_leave_max: int
    deamon_polling_rate: int

    audiomode: AudioMode = AudioMode.full
    microphone_index: int
    oww_model: str
    oww_sensitivity: float
    speech_recognition_model: str
    recognizer: RecognizerConfig
    wake_key: str

    student: StudentConfig

    aibackend: AIBackend
    openai_api_key: str
    openai_org_id: str
    assistant_id: str
    gpt_model: str
    gpt_prompt_pricing: float
    gpt_completion_pricing: float

    coach_events: List[CoachEvent] = [
        CoachEvent.wake,
        CoachEvent.game_start,
        CoachEvent.new_replay,
    ]

    obs_integration: bool
    sc2_client_url: str = "http://127.0.0.1:6119"
    screenshot: str
    tessdata_dir: str
    obs_ws_pw: str | None = None

    season: int

    ladder_maps: List[str]

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
