from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response

from src.api.errors import player_not_found, raise_api_error
from src.api.models import PlayerAliasResponse, PlayerInfoResponse, QueryRequest
from src.api.state import get_persistence
from src.api.validation import (
    parse_sort,
    validate_patch_document,
    validate_projection,
    validate_query_filter,
)
from src.persistence.replay_store import PlayerInfo


def _player_page_payload(page: Any) -> dict[str, Any]:
    payload = page.model_dump()
    payload["docs"] = [
        PlayerInfoResponse.from_player_info(player).model_dump() for player in page.docs
    ]
    return payload


def _portrait_asset(toon_handle: str, path: str, available: bool) -> dict[str, Any]:
    return {
        "available": available,
        "url": f"/api/players/{toon_handle}/{path}",
    }


def _player_portrait_metadata(player: PlayerInfo) -> dict[str, Any]:
    toon_handle = str(player.toon_handle)
    return {
        "toon_handle": toon_handle,
        "portrait": _portrait_asset(
            toon_handle,
            "portrait",
            player.portrait is not None,
        ),
        "portrait_constructed": _portrait_asset(
            toon_handle,
            "portrait/constructed",
            player.portrait_constructed is not None,
        ),
        "aliases": [
            {
                "index": alias_index,
                "name": alias.name,
                "portraits": [
                    {
                        "index": portrait_index,
                        "available": True,
                        "url": (
                            f"/api/players/{toon_handle}/aliases/"
                            f"{alias_index}/portraits/{portrait_index}"
                        ),
                    }
                    for portrait_index, _portrait in enumerate(alias.portraits)
                ],
            }
            for alias_index, alias in enumerate(player.aliases)
        ],
    }


def _missing_player_asset(toon_handle: str) -> None:
    raise_api_error(
        status_code=404,
        code="not_found",
        message="Document not found",
        details={"resource": "players", "id": toon_handle},
    )


def build_players_router() -> APIRouter:
    router = APIRouter(prefix="/api/players", tags=["players"])

    @router.get("")
    def list_players(
        request: Request,
        current_page: int = 1,
        docs_per_page: int = 50,
        sort: str | None = None,
        projection: str | None = "table",
        q: str | None = None,
        tag: str | None = None,
    ) -> dict[str, Any]:
        persistence = get_persistence(request)
        validate_projection(projection, allowed={None, "detail", "table"})
        page = persistence.replay_store.list_players(
            current_page=current_page,
            docs_per_page=docs_per_page,
            q=q,
            tag=tag,
            raw_sort=parse_sort(sort),
        )
        return _player_page_payload(page)

    @router.post("/query")
    def query_players(query: QueryRequest, request: Request) -> dict[str, Any]:
        persistence = get_persistence(request)
        validate_projection(query.projection, allowed={None, "detail", "table"})
        validate_query_filter(query.filter)
        page = persistence.replay_store.list_players(
            current_page=query.current_page,
            docs_per_page=query.docs_per_page,
            raw_query=query.filter,
            raw_sort=dict(query.sort) or None,
        )
        return _player_page_payload(page)

    @router.post("", response_model=PlayerInfoResponse)
    def create_player(player: PlayerInfo, request: Request) -> PlayerInfoResponse:
        persistence = get_persistence(request)
        created = persistence.replay_store.create_player(player)
        return PlayerInfoResponse.from_player_info(created)

    @router.post("/portrait-metadata")
    def get_bulk_player_portrait_metadata(
        body: dict[str, list[str]],
        request: Request,
    ) -> dict[str, Any]:
        persistence = get_persistence(request)
        items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for toon_handle in body.get("toon_handles", []):
            if toon_handle in seen:
                continue
            seen.add(toon_handle)
            player = persistence.replay_store.get_player_info(toon_handle)
            if player is None:
                continue
            items.append(_player_portrait_metadata(player))
        return {"items": items}

    @router.get("/{toon_handle}", response_model=PlayerInfoResponse)
    def get_player(toon_handle: str, request: Request) -> PlayerInfoResponse:
        persistence = get_persistence(request)
        player = persistence.replay_store.get_player_info(toon_handle)
        if player is None:
            player_not_found(toon_handle)
        assert player is not None
        return PlayerInfoResponse.from_player_info(player)

    @router.get("/{toon_handle}/portrait-metadata")
    def get_player_portrait_metadata(
        toon_handle: str, request: Request
    ) -> dict[str, Any]:
        persistence = get_persistence(request)
        player = persistence.replay_store.get_player_info(toon_handle)
        if player is None:
            player_not_found(toon_handle)
        assert player is not None
        return _player_portrait_metadata(player)

    @router.put("/{toon_handle}", response_model=PlayerInfoResponse)
    def replace_player(
        toon_handle: str,
        player: PlayerInfo,
        request: Request,
    ) -> PlayerInfoResponse:
        persistence = get_persistence(request)
        if str(player.id) != toon_handle or str(player.toon_handle) != toon_handle:
            from src.api.errors import raise_api_error

            raise_api_error(
                status_code=409,
                code="conflict",
                message="Path id and body id must match.",
                details={"resource": "players", "path_id": toon_handle},
            )
        replaced = persistence.replay_store.replace_player(toon_handle, player)
        return PlayerInfoResponse.from_player_info(replaced)

    @router.patch("/{toon_handle}", response_model=PlayerInfoResponse)
    def patch_player(
        toon_handle: str,
        patch: dict[str, Any],
        request: Request,
    ) -> PlayerInfoResponse:
        persistence = get_persistence(request)
        validate_patch_document(patch)
        if "id" in patch and str(patch["id"]) != toon_handle:
            from src.api.errors import raise_api_error

            raise_api_error(
                status_code=409,
                code="conflict",
                message="Path id and body id must match.",
                details={"resource": "players", "path_id": toon_handle},
            )
        if "toon_handle" in patch and str(patch["toon_handle"]) != toon_handle:
            from src.api.errors import raise_api_error

            raise_api_error(
                status_code=409,
                code="conflict",
                message="Path id and body id must match.",
                details={"resource": "players", "path_id": toon_handle},
            )
        player = persistence.replay_store.patch_player(toon_handle, patch)
        if player is None:
            player_not_found(toon_handle)
        assert player is not None
        return PlayerInfoResponse.from_player_info(player)

    @router.delete("/{toon_handle}", status_code=204)
    def delete_player(toon_handle: str, request: Request) -> Response:
        persistence = get_persistence(request)
        deleted = persistence.replay_store.delete_player(toon_handle)
        if not deleted:
            player_not_found(toon_handle)
        return Response(status_code=204)

    @router.get("/{toon_handle}/replays")
    def get_player_replays(
        toon_handle: str,
        request: Request,
        current_page: int = 1,
        docs_per_page: int = 50,
        sort: str | None = None,
        projection: str | None = "table",
    ):
        persistence = get_persistence(request)
        validate_projection(projection, allowed={None, "detail", "table"})
        player = persistence.replay_store.get_player_info(toon_handle)
        if player is None:
            player_not_found(toon_handle)
        return persistence.replay_store.list_replays(
            current_page=current_page,
            docs_per_page=docs_per_page,
            raw_query={"players.toon_handle": toon_handle},
            raw_sort=parse_sort(sort),
        )

    @router.get("/{toon_handle}/aliases", response_model=list[PlayerAliasResponse])
    def get_player_aliases(
        toon_handle: str,
        request: Request,
    ) -> list[PlayerAliasResponse]:
        persistence = get_persistence(request)
        player = persistence.replay_store.get_player_info(toon_handle)
        if player is None:
            player_not_found(toon_handle)
        assert player is not None
        return [PlayerAliasResponse.from_alias(alias) for alias in player.aliases]

    @router.get("/{toon_handle}/portrait")
    def get_player_portrait(toon_handle: str, request: Request) -> Response:
        persistence = get_persistence(request)
        player = persistence.replay_store.get_player_info(toon_handle)
        if player is None or player.portrait is None:
            _missing_player_asset(toon_handle)
        assert player.portrait is not None
        return Response(content=bytes(player.portrait), media_type="image/png")

    @router.get("/{toon_handle}/portrait/constructed")
    def get_player_constructed_portrait(toon_handle: str, request: Request) -> Response:
        persistence = get_persistence(request)
        player = persistence.replay_store.get_player_info(toon_handle)
        if player is None or player.portrait_constructed is None:
            _missing_player_asset(toon_handle)
        assert player.portrait_constructed is not None
        return Response(
            content=bytes(player.portrait_constructed),
            media_type="image/png",
        )

    @router.get("/{toon_handle}/aliases/{alias_index}/portraits/{portrait_index}")
    def get_player_alias_portrait(
        toon_handle: str,
        alias_index: int,
        portrait_index: int,
        request: Request,
    ) -> Response:
        persistence = get_persistence(request)
        player = persistence.replay_store.get_player_info(toon_handle)
        if player is None:
            _missing_player_asset(toon_handle)
        assert player is not None
        if alias_index < 0 or alias_index >= len(player.aliases):
            _missing_player_asset(toon_handle)
        alias = player.aliases[alias_index]
        if portrait_index < 0 or portrait_index >= len(alias.portraits):
            _missing_player_asset(toon_handle)
        return Response(
            content=bytes(alias.portraits[portrait_index]),
            media_type="image/png",
        )

    return router
