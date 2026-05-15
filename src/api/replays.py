from __future__ import annotations

from typing import Any

from pymongo import MongoClient

from src.api.config import ApiConfig
from src.api.contracts import (
    ConversationReviewLink,
    ReplayDetailResponse,
    ReplayMetadataResponse,
    ReplayPlayersResponse,
    ReplayPlayerSummary,
)


class ReplayQueryService:
    def __init__(self, config: ApiConfig):
        self._config = config
        self._client = MongoClient(str(config.mongo_dsn))

    @property
    def database(self):
        return self._client.get_database(self._config.db_name)

    @property
    def replay_collection(self):
        return self.database.get_collection("replays")

    @property
    def metadata_collection(self):
        return self.database.get_collection("meta")

    @property
    def player_collection(self):
        return self.database.get_collection("players")

    def get_replay_detail(self, replay_id: str) -> ReplayDetailResponse | None:
        replay = self.replay_collection.find_one({"_id": replay_id})
        if replay is None:
            return None

        players = replay.get("players") or []
        winning_player_name = next(
            (str(player.get("name")) for player in players if player.get("result") == "Win"),
            None,
        )
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

    def get_replay_metadata(self, replay_id: str) -> ReplayMetadataResponse | None:
        replay = self.replay_collection.find_one({"_id": replay_id}, {"_id": 1})
        if replay is None:
            return None

        metadata = self.metadata_collection.find_one({"replay": replay_id}) or {}
        conversation_id = metadata.get("replay_summary_conversation")

        return ReplayMetadataResponse(
            replay_id=replay_id,
            description=_optional_string(metadata.get("description")),
            tags=_string_list(metadata.get("tags")),
            replay_summary_conversation=(
                ConversationReviewLink(
                    id=str(conversation_id),
                    path=f"/conversations/{conversation_id}",
                )
                if conversation_id is not None
                else None
            ),
        )

    def get_replay_players(self, replay_id: str) -> ReplayPlayersResponse | None:
        replay = self.replay_collection.find_one({"_id": replay_id})
        if replay is None:
            return None

        player_documents = replay.get("players") or []
        toon_handles = [
            str(player.get("toon_handle"))
            for player in player_documents
            if player.get("toon_handle") is not None
        ]
        known_players = {
            str(player.get("_id")): player
            for player in self.player_collection.find({"_id": {"$in": toon_handles}})
        }

        return ReplayPlayersResponse(
            replay_id=replay_id,
            players=[
                _replay_player_summary(player, known_players.get(str(player.get("toon_handle"))))
                for player in player_documents
            ],
        )


def _matchup(players: list[dict[str, Any]]) -> str:
    races = [str(player.get("play_race") or "?")[:1].upper() for player in players]
    if not races:
        return "Unknown"
    return "v".join(races)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _replay_player_summary(
    player: dict[str, Any],
    known_player: dict[str, Any] | None,
) -> ReplayPlayerSummary:
    toon_handle = str(player.get("toon_handle") or "")
    return ReplayPlayerSummary(
        name=str(player.get("name") or toon_handle or "Unknown player"),
        toon_handle=toon_handle,
        play_race=str(player.get("play_race") or "Unknown"),
        result=str(player.get("result") or "Unknown"),
        scaled_rating=int(player.get("scaled_rating") or 0),
        avg_apm=float(player.get("avg_apm") or 0),
        player_record=(
            ConversationReviewLink(
                id=toon_handle,
                path=f"/players/{toon_handle}",
            )
            if known_player is not None
            else None
        ),
        aliases=_aliases(known_player),
    )


def _aliases(known_player: dict[str, Any] | None) -> list[str]:
    if known_player is None:
        return []

    aliases = known_player.get("aliases") or []
    names = [str(alias.get("name")) for alias in aliases if alias.get("name") is not None]
    return names