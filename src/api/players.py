from __future__ import annotations

import math
from typing import Any

from pymongo import DESCENDING, MongoClient

from src.api.config import ApiConfig
from src.api.contracts import (
    AliasPortraitAsset,
    PlayerAliasSummary,
    PlayerAliasesResponse,
    PlayerDetailResponse,
    PlayerListItem,
    PlayerListResponse,
    PlayerPortraitAsset,
    PlayerPortraitMetadataResponse,
    PlayerRelatedReplaysResponse,
    ReplayDetailResponse,
)

PNG_CONTENT_TYPE = "image/png"


class PlayerQueryService:
    def __init__(self, config: ApiConfig):
        self._config = config
        self._client = MongoClient(str(config.mongo_dsn))

    @property
    def database(self):
        return self._client.get_database(self._config.db_name)

    @property
    def player_collection(self):
        return self.database.get_collection("players")

    @property
    def replay_collection(self):
        return self.database.get_collection("replays")

    def list_players(
        self,
        *,
        page: int,
        page_size: int,
        q: str | None,
        tag: str | None,
    ) -> PlayerListResponse:
        query = _player_query(q=q, tag=tag)
        total = self.player_collection.count_documents(query)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        cursor = (
            self.player_collection.find(query)
            .sort([("name", 1), ("_id", 1)])
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        return PlayerListResponse(
            items=[_player_list_item(document) for document in cursor],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    def get_player_detail(self, toon_handle: str) -> PlayerDetailResponse | None:
        player = self.player_collection.find_one({"_id": toon_handle})
        if player is None:
            return None

        return PlayerDetailResponse(
            id=toon_handle,
            detail_path=f"/players/{toon_handle}",
            name=str(player.get("name") or toon_handle),
            toon_handle=toon_handle,
            alias_count=len(player.get("aliases") or []),
            tags=_string_list(player.get("tags")),
        )

    def get_player_aliases(self, toon_handle: str) -> PlayerAliasesResponse | None:
        player = self.player_collection.find_one({"_id": toon_handle})
        if player is None:
            return None

        return PlayerAliasesResponse(
            toon_handle=toon_handle,
            aliases=[
                _alias_summary(toon_handle, index, alias)
                for index, alias in enumerate(player.get("aliases") or [])
            ],
        )

    def get_player_portrait_metadata(
        self, toon_handle: str
    ) -> PlayerPortraitMetadataResponse | None:
        player = self.player_collection.find_one({"_id": toon_handle})
        if player is None:
            return None

        return PlayerPortraitMetadataResponse(
            toon_handle=toon_handle,
            portrait=_portrait_asset(
                toon_handle,
                suffix="portrait",
                payload=player.get("portrait"),
            ),
            portrait_constructed=_portrait_asset(
                toon_handle,
                suffix="portrait/constructed",
                payload=player.get("portrait_constructed"),
            ),
            aliases=[
                _alias_summary(toon_handle, index, alias)
                for index, alias in enumerate(player.get("aliases") or [])
            ],
        )

    def get_player_related_replays(
        self,
        toon_handle: str,
        *,
        limit: int = 10,
    ) -> PlayerRelatedReplaysResponse | None:
        player = self.player_collection.find_one({"_id": toon_handle}, {"_id": 1})
        if player is None:
            return None

        cursor = (
            self.replay_collection.find({"players.toon_handle": toon_handle})
            .sort("date", DESCENDING)
            .limit(limit)
        )
        return PlayerRelatedReplaysResponse(
            toon_handle=toon_handle,
            items=[_replay_detail(document) for document in cursor],
        )

    def get_player_portrait(self, toon_handle: str) -> bytes | None:
        player = self.player_collection.find_one({"_id": toon_handle}, {"portrait": 1})
        return _binary_bytes(player.get("portrait") if player is not None else None)

    def get_player_constructed_portrait(self, toon_handle: str) -> bytes | None:
        player = self.player_collection.find_one(
            {"_id": toon_handle},
            {"portrait_constructed": 1},
        )
        return _binary_bytes(
            player.get("portrait_constructed") if player is not None else None
        )

    def get_alias_portrait(
        self,
        toon_handle: str,
        *,
        alias_index: int,
        portrait_index: int,
    ) -> bytes | None:
        player = self.player_collection.find_one({"_id": toon_handle}, {"aliases": 1})
        if player is None:
            return None

        aliases = player.get("aliases") or []
        if alias_index < 0 or alias_index >= len(aliases):
            return None

        portraits = aliases[alias_index].get("portraits") or []
        if portrait_index < 0 or portrait_index >= len(portraits):
            return None

        return _binary_bytes(portraits[portrait_index])


def _player_query(*, q: str | None, tag: str | None) -> dict[str, Any]:
    clauses: list[dict[str, Any]] = []
    if q:
        clauses.append(
            {
                "$or": [
                    {"name": {"$regex": q, "$options": "i"}},
                    {"toon_handle": {"$regex": q, "$options": "i"}},
                    {"aliases.name": {"$regex": q, "$options": "i"}},
                ]
            }
        )
    if tag:
        clauses.append({"tags": tag})

    if not clauses:
        return {}
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _player_list_item(player: dict[str, Any]) -> PlayerListItem:
    toon_handle = str(player.get("_id") or player.get("toon_handle") or "")
    aliases = player.get("aliases") or []
    return PlayerListItem(
        id=toon_handle,
        detail_path=f"/players/{toon_handle}",
        name=str(player.get("name") or toon_handle or "Unknown player"),
        toon_handle=toon_handle,
        alias_count=len(aliases),
        last_seen_at=_last_seen_at(aliases),
        has_portrait=player.get("portrait") is not None,
        has_constructed_portrait=player.get("portrait_constructed") is not None,
    )


def _last_seen_at(aliases: list[dict[str, Any]]) -> Any:
    seen_values = [alias.get("seen_on") for alias in aliases if alias.get("seen_on") is not None]
    if not seen_values:
        return None
    return max(seen_values)


def _portrait_asset(toon_handle: str, *, suffix: str, payload: object) -> PlayerPortraitAsset:
    binary_payload = _binary_bytes(payload)
    if binary_payload is None:
        return PlayerPortraitAsset(available=False)
    return PlayerPortraitAsset(
        available=True,
        length=len(binary_payload),
        content_type=PNG_CONTENT_TYPE,
        url=f"/api/players/{toon_handle}/{suffix}",
    )


def _alias_summary(
    toon_handle: str,
    index: int,
    alias: dict[str, Any],
) -> PlayerAliasSummary:
    portraits = alias.get("portraits") or []
    return PlayerAliasSummary(
        index=index,
        name=str(alias.get("name") or f"Alias {index + 1}"),
        seen_on=alias.get("seen_on"),
        portraits=[
            AliasPortraitAsset(
                index=portrait_index,
                length=len(portrait_bytes),
                content_type=PNG_CONTENT_TYPE,
                url=(
                    f"/api/players/{toon_handle}/aliases/{index}/portraits/{portrait_index}"
                ),
            )
            for portrait_index, portrait_bytes in enumerate(_binary_sequence(portraits))
        ],
    )


def _binary_sequence(values: list[object]) -> list[bytes]:
    binary_values: list[bytes] = []
    for value in values:
        binary_value = _binary_bytes(value)
        if binary_value is not None:
            binary_values.append(binary_value)
    return binary_values


def _binary_bytes(value: object) -> bytes | None:
    if value is None:
        return None
    return bytes(value)


def _replay_detail(replay: dict[str, Any]) -> ReplayDetailResponse:
    players = replay.get("players") or []
    winning_player_name = next(
        (str(player.get("name")) for player in players if player.get("result") == "Win"),
        None,
    )
    replay_id = str(replay.get("_id") or "")
    return ReplayDetailResponse(
        id=replay_id,
        detail_path=f"/replays/{replay_id}",
        map_name=str(replay.get("map_name") or "Unknown map"),
        played_at=replay["date"],
        matchup=_matchup(players),
        game_type=str(replay.get("real_type") or replay.get("game_type") or "Unknown"),
        real_length_seconds=int(replay.get("real_length") or 0),
        player_count=len(players),
        winning_player_name=winning_player_name,
    )


def _matchup(players: list[dict[str, Any]]) -> str:
    races = [str(player.get("play_race") or "?")[:1].upper() for player in players]
    if not races:
        return "Unknown"
    return "v".join(races)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]