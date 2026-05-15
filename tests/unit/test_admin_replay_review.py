import pytest

from src.api.config import ApiConfig
from src.api.replays import ReplayQueryService
from src.persistence.replay_store import Metadata, PlayerInfo, ReplayStore
from src.replays.reader import ReplayReader


pytestmark = pytest.mark.mongo


@pytest.mark.parametrize(
    "replay_file",
    ["Site Delta LE (106) ZvZ 2base Muta into mass muta chaotic win.SC2Replay"],
    indirect=True,
)
def test_replay_query_service_returns_detail_metadata_and_joined_players(
    replay_store: ReplayStore,
    runtime_settings,
    replay_file: str,
):
    reader = ReplayReader(settings=runtime_settings)
    replay = reader.load_replay(replay_file)
    replay_store.upsert(replay)

    metadata = Metadata(
        replay=replay.id,
        description="Chaotic muta mirror with a decisive control swing.",
        tags=["muta", "zvz"],
        replay_summary_conversation="c" * 24,
    )
    replay_store.upsert(metadata)

    opponent = replay.get_opponent_of(runtime_settings.student.name)
    player = PlayerInfo(
        id=opponent.toon_handle,
        name=opponent.name,
        toon_handle=opponent.toon_handle,
        tags=["known-opponent"],
    )
    player.update_aliases(seen_on=replay.date)
    replay_store.upsert(player)

    service = ReplayQueryService(
        ApiConfig(
            mongo_dsn=replay_store.database.config.mongo_uri,
            db_name=replay_store.database.config.db_name,
        )
    )

    detail = service.get_replay_detail(replay.id)
    replay_metadata = service.get_replay_metadata(replay.id)
    replay_players = service.get_replay_players(replay.id)

    assert detail is not None
    assert detail.id == replay.id
    assert detail.detail_path == f"/replays/{replay.id}"
    assert detail.map_name == replay.map_name
    assert detail.player_count == len(replay.players)
    assert detail.winning_player_name in {player.name for player in replay.players}

    assert replay_metadata is not None
    assert replay_metadata.replay_id == replay.id
    assert replay_metadata.description == metadata.description
    assert replay_metadata.tags == metadata.tags
    assert replay_metadata.replay_summary_conversation is not None
    assert replay_metadata.replay_summary_conversation.id == "c" * 24
    assert replay_metadata.replay_summary_conversation.path == f"/conversations/{'c' * 24}"

    assert replay_players is not None
    assert replay_players.replay_id == replay.id
    assert len(replay_players.players) == len(replay.players)

    linked_player = next(
        player_item
        for player_item in replay_players.players
        if player_item.toon_handle == opponent.toon_handle
    )
    assert linked_player.player_record is not None
    assert linked_player.player_record.id == opponent.toon_handle
    assert linked_player.player_record.path == f"/players/{opponent.toon_handle}"
    assert linked_player.aliases == [opponent.name]
