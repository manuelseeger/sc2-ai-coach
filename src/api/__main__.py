from __future__ import annotations

import uvicorn

from src.api.app import create_app
from src.api.config import ApiConfig


def main() -> None:
    config = ApiConfig()
    uvicorn.run(create_app(config), host=config.host, port=config.port)


if __name__ == "__main__":
    main()
