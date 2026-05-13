from src.runtime.playeridentity import build_player_identity_services


def test_build_player_identity_services_shares_replay_store_and_portrait_source(
    runtime_settings, mocker
):
    replay_store = mocker.Mock()
    sc2pulse = mocker.Mock()
    sc2client = mocker.Mock()

    services = build_player_identity_services(
        runtime_settings,
        replay_store=replay_store,
        sc2pulse=sc2pulse,
        sc2client=sc2client,
    )

    assert services.resolver.replay_store is replay_store
    assert services.enricher.replay_store is replay_store
    assert services.resolver.sc2pulse is sc2pulse
    assert services.resolver.sc2client is sc2client
    assert services.resolver.portrait_source is services.portrait_source
    assert services.enricher.portrait_source is services.portrait_source
