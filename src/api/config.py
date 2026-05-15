from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import Field
from pydantic.networks import UrlConstraints
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

MongoDsn = Annotated[
    MultiHostUrl,
    UrlConstraints(allowed_schemes=["mongodb", "mongodb+srv"]),
]


class ApiConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AICOACH_",
        extra="ignore",
        env_nested_delimiter="__",
    )

    mongo_dsn: MongoDsn = "mongodb://localhost:27017"
    db_name: str = "SC2AICOACH"
    host: str = "127.0.0.1"
    port: int = 8765
    web_dist_dir: Path = Path("webapp/dist")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    mongo_connect_timeout_ms: int = 1000
