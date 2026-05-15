from io import BytesIO

import pytest
from PIL import Image

from src.api.config import ApiConfig
from src.api.players import PlayerQueryService
from src.persistence.replay_store import PlayerInfo, ReplayStore
from src.replays.reader import ReplayReader
from src.replays.types import to_bson_binary


pytestmark = pytest.mark.mongo


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (8, 8), color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.parametrize(
    "replay_file",
    ["Site Delta LE (106) ZvZ 2base Muta into mass muta chaotic win.SC2Replay"],
    indirect=True,
)
def test_player_query_service_returns_review_detail_portraits_and_related_replays(
    replay_store: ReplayStore,
    runtime_settings,
    replay_file: str,
):
    reader = ReplayReader(settings=runtime_settings)
    replay = reader.load_replay(replay_file)
    replay_store.upsert(replay)

    opponent = replay.get_opponent_of(runtime_settings.student.name)
    portrait = _png_bytes((180, 90, 40))
    constructed = _png_bytes((30, 60, 180))
    alias_portrait = _png_bytes((40, 180, 90))
    player = PlayerInfo(
        id=opponent.toon_handle,
        name=opponent.name,
        toon_handle=opponent.toon_handle,
        portrait=to_bson_binary(portrait),
        portrait_constructed=to_bson_binary(constructed),
        tags=["known-opponent"],
    )
    player.update_aliases(seen_on=replay.date)
    player.aliases[0].portraits.append(to_bson_binary(alias_portrait))
    replay_store.upsert(player)

    service = PlayerQueryService(
        ApiConfig(
            mongo_dsn=replay_store.database.config.mongo_uri,
            db_name=replay_store.database.config.db_name,
        )
    )

    detail = service.get_player_detail(opponent.toon_handle)
    aliases = service.get_player_aliases(opponent.toon_handle)
    portrait_metadata = service.get_player_portrait_metadata(opponent.toon_handle)
    related_replays = service.get_player_related_replays(opponent.toon_handle)
    primary_portrait = service.get_player_portrait(opponent.toon_handle)
    constructed_portrait = service.get_player_constructed_portrait(opponent.toon_handle)
    alias_portrait_bytes = service.get_alias_portrait(
        opponent.toon_handle,
        alias_index=0,
        portrait_index=1,
    )

    assert detail is not None
    assert detail.id == opponent.toon_handle
    assert detail.detail_path == f"/players/{opponent.toon_handle}"
    assert detail.name == opponent.name
    assert detail.tags == ["known-opponent"]

    assert aliases is not None
    assert aliases.toon_handle == opponent.toon_handle
    assert aliases.aliases[0].name == opponent.name
    assert aliases.aliases[0].portraits[1].url == (
        f"/api/players/{opponent.toon_handle}/aliases/0/portraits/1"
    )

    assert portrait_metadata is not None
    assert portrait_metadata.portrait.available is True
    assert portrait_metadata.portrait.url == f"/api/players/{opponent.toon_handle}/portrait"
    assert portrait_metadata.portrait_constructed.available is True
    assert portrait_metadata.portrait_constructed.url == (
        f"/api/players/{opponent.toon_handle}/portrait/constructed"
    )

    assert related_replays is not None
    assert related_replays.toon_handle == opponent.toon_handle
    assert related_replays.items[0].id == replay.id
    assert related_replays.items[0].detail_path == f"/replays/{replay.id}"

    assert primary_portrait == portrait
    assert constructed_portrait == constructed
    assert alias_portrait_bytes == alias_portrait