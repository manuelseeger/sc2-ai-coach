from __future__ import annotations

import uvicorn

from src.api.app import app
from src.runtime.settings import load_api_settings


def main() -> None:
    settings = load_api_settings()
    uvicorn.run(app, host=settings.api.host, port=settings.api.port)


if __name__ == "__main__":
    main()
