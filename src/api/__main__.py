from __future__ import annotations

import uvicorn

from api.app import app
from runtime.settings import load_api_settings


def main() -> None:
    settings = load_api_settings()
    uvicorn.run(app, host=settings.api.host, port=settings.api.port)


if __name__ == "__main__":
    main()
