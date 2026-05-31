from datetime import datetime
from enum import Enum
from functools import cached_property
from glob import glob
from os.path import join
from typing import Annotated, Dict, List, Literal, Optional, Tuple, Type

from pydantic import (
    BaseModel,
    DirectoryPath,
    Field,
    FilePath,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)
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

from src.ai.pricing import (
    ModelPricing,
    ModelPricingOverride,
    get_default_model_pricing,
    normalize_model_name,
)
from src.api.config import ApiConfig
from src.runtime.audio_devices import select_preferred_microphone_index

MongoSRVDsn = Annotated[
    MultiHostUrl, UrlConstraints(allowed_schemes=["mongodb+srv", "mongodb"])
]


def sort_config_files(files):
    def key_func(filename: str):
        return (not filename.startswith("."), filename.count("."))

    return sorted(files, key=key_func)


yaml_files = sort_config_files(glob("config*.yml"))
env_files = sort_config_files(glob(".env*"))
if ".env.example" in env_files:
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


class TranscriberBackend(str, Enum):
    whisper = "whisper"
    canary_qwen = "canary_qwen"
    xai = "xai"


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


class TwitchConfig(BaseModel):
    client_id: str
    client_secret: str
    channel: str
    mocked: bool = False
    mocked_user_id: str | None = None

    @model_validator(mode="after")
    def validate_mocked_user_fields(self):
        if self.mocked and self.mocked_user_id is None:
            raise ValueError("mocked_user_id is required when twitch.mocked is enabled")
        return self


ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]


class WakeWordConfig(BaseModel):
    engine: Literal["livekit"] = "livekit"
    model_path: FilePath
    threshold: float = 0.55


class ApiSettings(BaseSettings):
    """API-safe settings slice.

    Holds only the settings the standalone API needs, all defaulted, so it loads
    even when every coach-only setting is absent (e.g. a deployment running on
    defaults + env vars). ``Config`` extends this with the coach-runtime fields.
    """

    model_config = SettingsConfigDict(
        yaml_file=yaml_files,
        env_file=env_files,
        env_prefix="AICOACH_",
        extra="ignore",
        env_nested_delimiter="__",
    )

    db_name: str = "SC2AICOACH"
    mongo_dsn: MongoSRVDsn = "mongodb://localhost:28765/SC2AICOACH"  # pyright: ignore[reportAssignmentType]
    student: StudentConfig = Field(
        default_factory=lambda: StudentConfig(name="Player", race="Terran")
    )
    season_start: Optional[datetime] = None
    api: ApiConfig = Field(default_factory=ApiConfig)

    @classmethod
    def settings_customise_sources(  # type: ignore[override]
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


class Config(ApiSettings):
    # model_config + settings_customise_sources inherited from ApiSettings
    name: str = "AICoach"
    replay_folder: str
    instant_leave_max: int
    deamon_polling_rate: int

    audiomode: AudioMode = AudioMode.full
    microphone_index: int | None = None
    wakeword: WakeWordConfig
    speech_recognition_model: str
    transcriber_backend: TranscriberBackend = TranscriberBackend.whisper
    xai_api_key: Optional[str] = None
    xai_stt_language: str = "en"
    recognizer: RecognizerConfig
    wake_key: str
    interactive: bool = True

    tts: TTSConfig

    # Re-declared without a default to keep coach validation strict (overrides the
    # API-safe default on ApiSettings, so the coach still fails loudly when missing).
    student: StudentConfig  # pyright: ignore[reportGeneralTypeIssues]

    aibackend: AIBackend
    openai_endpoint: Optional[str] = None
    openai_api_key: str
    openai_org_id: str
    gpt_model: str
    gpt_prompt_pricing_per_million: float | None = None
    gpt_cached_prompt_pricing_per_million: float | None = None
    gpt_completion_pricing_per_million: float | None = None
    model_pricing_per_million: dict[str, ModelPricingOverride] = Field(
        default_factory=dict
    )
    reasoning_effort: ReasoningEffort | None = "medium"
    reasoning_continuity_enabled: bool = False

    @field_validator("model_pricing_per_million", mode="before")
    @classmethod
    def _normalize_model_pricing_keys(cls, value):
        if value is None:
            return {}
        return {
            normalize_model_name(model_name) or model_name: override
            for model_name, override in value.items()
        }

    @model_validator(mode="after")
    def _resolve_microphone_index(self):
        if self.microphone_index is None and self.audiomode in [
            AudioMode.voice_in,
            AudioMode.full,
        ]:
            self.microphone_index = select_preferred_microphone_index()
        return self

    def get_model_pricing(self, model_name: str | None = None) -> ModelPricing:
        resolved_model = normalize_model_name(model_name or self.gpt_model)
        configured_model = normalize_model_name(self.gpt_model)
        pricing = get_default_model_pricing(resolved_model)
        if pricing is None and resolved_model != configured_model:
            pricing = get_default_model_pricing(configured_model)
        pricing = pricing or ModelPricing(
            prompt_per_million=0,
            cached_prompt_per_million=0,
            completion_per_million=0,
        )

        override = self.model_pricing_per_million.get(resolved_model or "")
        if override is not None:
            if override.prompt_per_million is not None:
                pricing.prompt_per_million = override.prompt_per_million
            if override.cached_prompt_per_million is not None:
                pricing.cached_prompt_per_million = override.cached_prompt_per_million
            if override.completion_per_million is not None:
                pricing.completion_per_million = override.completion_per_million

        if resolved_model == configured_model or (
            resolved_model != configured_model
            and get_default_model_pricing(resolved_model) is None
            and override is None
        ):
            if self.gpt_prompt_pricing_per_million is not None:
                pricing.prompt_per_million = self.gpt_prompt_pricing_per_million
            if self.gpt_cached_prompt_pricing_per_million is not None:
                pricing.cached_prompt_per_million = (
                    self.gpt_cached_prompt_pricing_per_million
                )
            if self.gpt_completion_pricing_per_million is not None:
                pricing.completion_per_million = self.gpt_completion_pricing_per_million

        return pricing

    @property
    def gpt_prompt_pricing(self) -> float:
        return self.get_model_pricing().prompt

    @property
    def gpt_cached_prompt_pricing(self) -> float:
        return self.get_model_pricing().cached_prompt

    @property
    def gpt_completion_pricing(self) -> float:
        return self.get_model_pricing().completion

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
    reader_cache_dir: Optional[DirectoryPath] = None

    twitch: TwitchConfig | None = None

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

    ladder_maps: List[str]

    default_projection: Dict[str, int]

    # Re-declared without a default to keep coach validation strict (overrides the
    # API-safe default on ApiSettings). mongo_dsn / season_start / api keep the
    # inherited defaults.
    db_name: str  # pyright: ignore[reportGeneralTypeIssues]


class SettingsLoaderError(Exception):
    pass


def load_current_settings() -> Config:
    try:
        settings = Config()  # type: ignore
    except ValidationError as exc:
        raise SettingsLoaderError("Failed to load runtime settings") from exc

    return settings


def load_api_settings() -> ApiSettings:
    try:
        return ApiSettings()  # type: ignore
    except ValidationError as exc:
        raise SettingsLoaderError("Failed to load API settings") from exc


_config_cache: Config | None = None


def get_config() -> Config:
    global _config_cache
    if _config_cache is None:
        _config_cache = load_current_settings()
    return _config_cache
