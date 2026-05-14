from src.runtime.playeridentity import build_player_identity_services
from src.util import is_barcode


def _seeded_named_student_replay(seeded_replay_mongo_container):
    runtime_settings = seeded_replay_mongo_container.settings
    return next(
        replay
        for replay in seeded_replay_mongo_container.seeded_replays
        if any(
            player.name == runtime_settings.student.name for player in replay.players
        )
        and not is_barcode(replay.get_opponent_of(runtime_settings.student.name).name)
    )


def test_build_player_identity_services_enriches_then_resolves_from_shared_store(
    seeded_replay_mongo_container,
):
    runtime_settings = seeded_replay_mongo_container.settings.model_copy(deep=True)
    replay_store = seeded_replay_mongo_container.replay_store
    replay = _seeded_named_student_replay(seeded_replay_mongo_container)
    opponent = replay.get_opponent_of(runtime_settings.student.name)

    services = build_player_identity_services(
        runtime_settings,
        replay_store=replay_store,
    )

    saved_player_info = services.enricher.save_from_replay(replay)
    resolved_player_info = services.resolver.resolve_player(
        opponent=opponent.name,
        mapname=replay.map_name,
        mmr=opponent.scaled_rating,
    )

    assert resolved_player_info is not None
    assert resolved_player_info.id == saved_player_info.id
    assert resolved_player_info.toon_handle == saved_player_info.toon_handle
    assert resolved_player_info.name == opponent.name
