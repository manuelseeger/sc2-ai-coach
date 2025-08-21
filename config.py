import sys
from datetime import datetime
from enum import Enum
from functools import cached_property
from glob import glob
from os.path import join
from pathlib import Path
from typing import Annotated, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, DirectoryPath, ValidationError, computed_field
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
from rich import print

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


class SC2Region(str, Enum):
    US = "US"
    EU = "EU"
    KR = "KR"
    CN = "CN"

    def __str__(self) -> str:
        return self.value


class CoachEvent(str, Enum):
    wake = "wake"
    game_start = "game_start"
    new_replay = "new_replay"
    twitch = "twitch"


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


class TTSConfig(BaseModel):
    engine: str = "system"
    voice: Optional[str] = None
    speed: Optional[float] = 1.0


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        yaml_file=yaml_files,
        env_file=env_files,
        env_prefix="AICOACH_",
        extra="ignore",
        env_nested_delimiter="__",
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
    interactive: bool = True

    tts: TTSConfig

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

    blizzard_client_id: Optional[str] = None
    blizzard_client_secret: Optional[str] = None
    blizzard_region: SC2Region
    bnet_cache_dir: Optional[DirectoryPath] = None
    include_map_details: bool = True

    twitch_client_id: Optional[str] = None
    twitch_client_secret: Optional[str] = None
    twitch_channel: Optional[str] = None
    twitch_mocked: bool = False
    twitch_mocked_user_id: Optional[str] = None

    rating_delta_max: int
    rating_delta_max_barcode: int
    last_played_ago_max: int
    match_history_depth: int

    log_dir: DirectoryPath
    obs_dir: DirectoryPath

    @computed_field
    @cached_property
    def screenshot(self) -> str:
        return join(self.obs_dir, "screenshots", "_maploading.png")

    tessdata_dir: str
    obs_ws_pw: str | None = None

    season: int

    season_start: Optional[datetime] = None

    ladder_maps: List[str]

    default_projection: Dict[str, int]

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

    def is_initial(self) -> bool:
        """Check if the environment is initialized

        Right now this doesn't do anything pydantic doesn't do already.
        But this can be extended in the future to check for example if mongodb views are created.
        """
        return not Path(self.obs_dir).exists()

    @classmethod
    def check_initial(cls):
        try:
            config: Config = cls()  # type: ignore
        except ValidationError as e:
            print(e)
            sys.exit(1)
        if config.is_initial():
            from rich.prompt import Confirm

            do_init = Confirm.ask("Can't find initialized environment. Initialize now?")
            if do_init:
                config.init()
                print("Initialized environment :white_heavy_check_mark:")
            else:
                sys.exit(0)
        return config

    def init(self):
        Path(join(self.obs_dir, "screenshots")).mkdir(parents=True, exist_ok=True)
        Path(join(self.log_dir)).mkdir(parents=True, exist_ok=True)

        if self.obs_integration:
            from openwakeword.utils import download_models

            download_models()

            from src.io.tts import init_tts

            init_tts()


config: Config = Config.check_initial()
