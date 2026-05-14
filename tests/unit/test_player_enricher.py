from src.playeridentity import PlayerIdentityEnricher, PlayerIdentityEnrichmentError
from src.replays.types import Replay


def test_player_identity_enricher_raises_typed_error_on_unacknowledged_save(
    runtime_settings, mocker
):
    portrait_source = mocker.Mock()
    portrait_source.get_matching_portrait_from_replay.return_value = None
    portrait_source.portrait_construct_from_bnet.return_value = None
    replay_store = mocker.Mock()
    replay_store.find.return_value = None
    replay_store.upsert.return_value = mocker.Mock(acknowledged=False)

    enricher = PlayerIdentityEnricher(
        runtime_settings,
        replay_store=replay_store,
        portrait_source=portrait_source,
    )

    replay = Replay.model_construct(id="a" * 64)
    opponent = mocker.Mock(
        name="KnownOpponent", toon_handle="2-S2-1-6861867", toon_id=1
    )
    replay.get_opponent_of.return_value = opponent

    try:
        enricher.save_from_replay(replay)
        raise AssertionError("Expected PlayerIdentityEnrichmentError")
    except PlayerIdentityEnrichmentError as exc:
        assert exc.opponent_name == "KnownOpponent"
        assert exc.toon_handle == "2-S2-1-6861867"


def test_player_identity_enricher_allows_optional_portrait_misses(
    runtime_settings, mocker
):
    portrait_source = mocker.Mock()
    portrait_source.get_matching_portrait_from_replay.return_value = None
    portrait_source.portrait_construct_from_bnet.return_value = None
    replay_store = mocker.Mock()
    replay_store.find.return_value = None
    replay_store.upsert.return_value = mocker.Mock(acknowledged=True)

    enricher = PlayerIdentityEnricher(
        runtime_settings,
        replay_store=replay_store,
        portrait_source=portrait_source,
    )

    replay = Replay.model_construct(id="a" * 64)
    opponent = mocker.Mock(
        name="KnownOpponent", toon_handle="2-S2-1-6861867", toon_id=1
    )
    replay.get_opponent_of.return_value = opponent

    player_info = enricher.save_from_replay(replay)

    assert player_info.name == "KnownOpponent"
    assert player_info.portrait is None
    assert player_info.portrait_constructed is None
