from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class ApiConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765
    web_dist_dir: Path = Path("webapp/dist")
    mongo_connect_timeout_ms: int = 1000
