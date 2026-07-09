"""Real end-to-end clan-tag resolution against a temporary Mongo container.

Uses the seeded test database. It looks for a seeded replay whose (non-student)
opponent carries a clan tag, enriches player identity from that real replay, then
proves the clan tag both (a) gets persisted and (b) disambiguates an otherwise
ambiguous same-named opponent.

If the seeded test data contains no clan-tagged opponent, the tests skip rather
than fail (drop such a replay into ``tests/testdata/replays`` to enable them).
"""

import pytest

from src.persistence.replay_store import PlayerInfo
from src.runtime.playeridentity import build_player_identity_services


def _clan_replay(container):
    settings = container.settings
    for replay in container.seeded_replays:
        if not any(p.name == settings.student.name for p in replay.players):
            continue
        opponent = replay.get_opponent_of(settings.student.name)
        if opponent.clan_tag:
            return replay, opponent
    pytest.skip("No seeded replay with a clan-tagged opponent")


def test_enrich_persists_clan_tag_from_replay(seeded_replay_mongo_container):
    container = seeded_replay_mongo_container
    settings = container.settings.model_copy(deep=True)
    replay, opponent = _clan_replay(container)

    services = build_player_identity_services(
        settings, replay_store=container.replay_store
    )
    saved = services.enricher.save_from_replay(replay)

    # The clan tag from the real replay is persisted on the player and the alias.
    assert saved.clan_tag == opponent.clan_tag
    assert any(alias.clan_tag == opponent.clan_tag for alias in saved.aliases)


def test_clan_tag_disambiguates_same_named_opponent(seeded_replay_mongo_container):
    container = seeded_replay_mongo_container
    settings = container.settings.model_copy(deep=True)
    replay, opponent = _clan_replay(container)

    services = build_player_identity_services(
        settings, replay_store=container.replay_store
    )
    saved = services.enricher.save_from_replay(replay)

    # Introduce a same-named decoy in a different clan -> name alone is ambiguous.
    decoy_handle = "2-S2-9-9999999"
    decoy = PlayerInfo(
        id=decoy_handle,
        name=opponent.name,
        toon_handle=decoy_handle,
        clan_tag="OTHER",
    )
    decoy.update_aliases()
    container.replay_store.create_player(decoy)

    # Plain name resolution can no longer pick a single player.
    assert services.resolver._resolve_by_name(opponent.name) is None

    # The clan tag uniquely identifies the real opponent end-to-end.
    resolved = services.resolver.resolve_player(
        opponent=opponent.name,
        mapname=replay.map_name,
        mmr=opponent.scaled_rating,
        clan=opponent.clan_tag,
    )

    assert resolved is not None
    assert resolved.toon_handle == saved.toon_handle
    assert resolved.clan_tag == opponent.clan_tag
