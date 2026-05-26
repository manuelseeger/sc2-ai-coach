import asyncio
from pathlib import Path

import httpx

HOST = "https://vespene.gg"
DESTINATION = Path("assets/sprites")
SPRITES_FILE = Path(__file__).parent / "sprites.txt"


async def download_all() -> None:
    paths = [line.strip() for line in SPRITES_FILE.read_text().splitlines() if line.strip()]

    async with httpx.AsyncClient(base_url=HOST, follow_redirects=True) as client:
        for sprite_path in paths:
            dest = DESTINATION / sprite_path.lstrip("/")
            if dest.exists():
                print(f"skip  {sprite_path}")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            response = await client.get(sprite_path)
            response.raise_for_status()
            dest.write_bytes(response.content)
            print(f"saved {sprite_path}")


if __name__ == "__main__":
    asyncio.run(download_all())

