from src.playeridentity import PlayerIdentityEnricher
from src.replays.types import Replay


def _seeded_student_replay(seeded_replay_mongo_container) -> Replay:
    runtime_settings = seeded_replay_mongo_container.settings
    return next(
        replay
        for replay in seeded_replay_mongo_container.seeded_replays
        if any(
            player.name == runtime_settings.student.name for player in replay.players
        )
    )


def test_player_identity_enricher_persists_player_info_in_seeded_store(
    seeded_replay_mongo_container,
):
    runtime_settings = seeded_replay_mongo_container.settings.model_copy(deep=True)
    replay_store = seeded_replay_mongo_container.replay_store
    replay = _seeded_student_replay(seeded_replay_mongo_container)
    opponent = replay.get_opponent_of(runtime_settings.student.name)

    player_info = PlayerIdentityEnricher(
        runtime_settings,
        replay_store=replay_store,
    ).save_from_replay(replay)
    stored_player_info = replay_store.find(player_info)

    assert stored_player_info is not None
    assert player_info.toon_handle == opponent.toon_handle
    assert stored_player_info.name == opponent.name
    assert stored_player_info.toon_handle == opponent.toon_handle

    assert any(alias.name == opponent.name for alias in stored_player_info.aliases)


def test_player_identity_enricher_updates_aliases_for_existing_player_in_seeded_store(
    seeded_replay_mongo_container,
):
    runtime_settings = seeded_replay_mongo_container.settings.model_copy(deep=True)
    replay_store = seeded_replay_mongo_container.replay_store
    replay = _seeded_student_replay(seeded_replay_mongo_container)
    opponent = replay.get_opponent_of(runtime_settings.student.name)
    aliased_replay = replay.model_copy(deep=True)
    aliased_opponent = aliased_replay.get_opponent_of(runtime_settings.student.name)
    aliased_name = f"{opponent.name}_alt"
    aliased_opponent.name = aliased_name

    enricher = PlayerIdentityEnricher(
        runtime_settings,
        replay_store=replay_store,
    )

    original_player_info = enricher.save_from_replay(replay)
    updated_player_info = enricher.save_from_replay(aliased_replay)
    stored_player_info = replay_store.find(original_player_info)

    assert updated_player_info.toon_handle == opponent.toon_handle
    assert stored_player_info is not None
    assert stored_player_info.name == aliased_name
    assert {alias.name for alias in stored_player_info.aliases} >= {
        opponent.name,
        aliased_name,
    }
    assert (
        replay_store.database.raw["players"].count_documents(
            {"_id": opponent.toon_handle}
        )
        == 1
    )
