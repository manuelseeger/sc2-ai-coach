from __future__ import annotations

from dataclasses import dataclass

from src.playeridentity import PlayerIdentityEnricher, PlayerPortraitSource
from src.playerresolver import PlayerResolver


@dataclass(frozen=True)
class PlayerIdentityServices:
    portrait_source: PlayerPortraitSource
    enricher: PlayerIdentityEnricher
    resolver: PlayerResolver


def build_player_identity_services(
    settings,
    *,
    replay_store=None,
    sc2pulse=None,
    sc2client=None,
) -> PlayerIdentityServices:
    portrait_source = PlayerPortraitSource(settings)
    return PlayerIdentityServices(
        portrait_source=portrait_source,
        enricher=PlayerIdentityEnricher(
            settings,
            replay_store=replay_store,
            portrait_source=portrait_source,
        ),
        resolver=PlayerResolver(
            settings,
            replay_store=replay_store,
            sc2pulse=sc2pulse,
            sc2client=sc2client,
            portrait_source=portrait_source,
        ),
    )


__all__ = ["PlayerIdentityServices", "build_player_identity_services"]
