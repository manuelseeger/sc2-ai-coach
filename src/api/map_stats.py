from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from functools import cached_property
from glob import glob
from pathlib import Path
from typing import Any

import yaml
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pydantic import BaseModel, ValidationError

from src.api.config import ApiConfig
from src.api.contracts import (
    MapStatsDateRange,
    MapStatsListResponse,
    MapStatsMetricSummary,
    MapStatsNamedRange,
    MapStatsQueryGroup,
    MapStatsQueryRequest,
    MapStatsQueryResponse,
    MapStatsRangeSummary,
    MapStatsRangesResponse,
    MapStatsSummary,
)

_DEFAULT_UNAVAILABLE_REASON = (
    "Map stats are unavailable until the admin API can resolve student and season "
    "settings without loading the live runtime."
)
_ALLOWED_GROUP_BY = {
    "map",
    "matchup",
    "player_race",
    "opponent_race",
    "result",
    "date_day",
    "date_week",
    "date_month",
}
_ALLOWED_METRICS = {"games", "wins", "losses", "winrate"}
_ALLOWED_FILTER_OPERATORS = {
    "$and",
    "$or",
    "$nor",
    "$not",
    "$eq",
    "$ne",
    "$in",
    "$nin",
    "$gt",
    "$gte",
    "$lt",
    "$lte",
    "$exists",
    "$regex",
    "$elemMatch",
}


class MapStatsUnavailableError(RuntimeError):
    pass


class InvalidMapStatsQueryError(ValueError):
    pass


class MapStatsRuntimeConfig(BaseModel):
    student_name: str
    student_race: str
    season_start: datetime | None = None


class MapStatsQueryService:
    def __init__(
        self,
        config: ApiConfig,
        *,
        runtime_config: MapStatsRuntimeConfig | None = None,
        unavailable_reason: str | None = None,
    ):
        self._config = config
        self._client = MongoClient(
            str(config.mongo_dsn),
            serverSelectionTimeoutMS=config.mongo_connect_timeout_ms,
        )
        self._runtime_config = runtime_config
        self._unavailable_reason = unavailable_reason

    @classmethod
    def from_api_config(cls, config: ApiConfig) -> MapStatsQueryService:
        runtime_config, unavailable_reason = load_map_stats_runtime_config()
        return cls(
            config,
            runtime_config=runtime_config,
            unavailable_reason=unavailable_reason,
        )

    @property
    def available(self) -> bool:
        return self._runtime_config is not None

    @property
    def unavailable_reason(self) -> str:
        return self._unavailable_reason or _DEFAULT_UNAVAILABLE_REASON

    @cached_property
    def database(self):
        return self._client.get_database(self._config.db_name)

    @cached_property
    def collection(self):
        return self.database.get_collection("replays")

    def list_map_stats(
        self,
        *,
        map_name: str | None,
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> MapStatsListResponse:
        self._ensure_available()
        date_range = MapStatsDateRange(from_date=from_date, to_date=to_date)
        summaries = self._aggregate_map_summaries(map_name=map_name, date_range=date_range)
        return MapStatsListResponse(
            items=summaries,
            selected_map=map_name,
            date_range=date_range,
        )

    def get_map_stats(
        self,
        map_name: str,
        *,
        from_date: datetime | None,
        to_date: datetime | None,
    ) -> MapStatsSummary | None:
        self._ensure_available()
        summaries = self._aggregate_map_summaries(
            map_name=map_name,
            date_range=MapStatsDateRange(from_date=from_date, to_date=to_date),
        )
        if not summaries:
            return None
        return summaries[0]

    def get_map_stats_ranges(
        self,
        map_name: str,
        *,
        ranges: list[MapStatsNamedRange],
    ) -> MapStatsRangesResponse:
        self._ensure_available()
        return MapStatsRangesResponse(
            map=map_name,
            ranges=[
                MapStatsRangeSummary(
                    name=range_item.name,
                    from_date=range_item.from_date,
                    to_date=range_item.to_date,
                    stats=self.get_map_stats(
                        map_name,
                        from_date=range_item.from_date,
                        to_date=range_item.to_date,
                    ),
                )
                for range_item in ranges
            ],
        )

    def query_map_stats(self, request: MapStatsQueryRequest) -> MapStatsQueryResponse:
        self._ensure_available()
        group_by = _validate_group_by(request.group_by)
        metrics = _validate_metrics(request.metrics)
        if request.limit < 1 or request.limit > 500:
            raise InvalidMapStatsQueryError("Map stats query limit must be between 1 and 500.")
        _validate_filter(request.filter)

        pipeline = self._grouped_query_pipeline(
            filter_document=request.filter,
            date_range=request.date_range,
            group_by=group_by,
            limit=request.limit,
        )
        groups = [
            _project_group_result(document, metrics=metrics)
            for document in self.collection.aggregate(pipeline)
        ]
        groups_by_key = {
            _group_key_token(group.key): group.model_copy(deep=True) for group in groups
        }

        for range_item in request.ranges:
            range_pipeline = self._grouped_query_pipeline(
                filter_document=request.filter,
                date_range=MapStatsDateRange(
                    from_date=range_item.from_date,
                    to_date=range_item.to_date,
                ),
                group_by=group_by,
                limit=request.limit,
            )
            for document in self.collection.aggregate(range_pipeline):
                range_group = _project_group_result(document, metrics=list(_ALLOWED_METRICS))
                token = _group_key_token(range_group.key)
                if token not in groups_by_key:
                    groups_by_key[token] = MapStatsQueryGroup(key=range_group.key)
                if groups_by_key[token].ranges is None:
                    groups_by_key[token].ranges = {}
                groups_by_key[token].ranges[range_item.name] = MapStatsMetricSummary(
                    games=range_group.games or 0,
                    wins=range_group.wins or 0,
                    losses=range_group.losses or 0,
                    winrate=range_group.winrate or 0.0,
                )

        result_groups = list(groups_by_key.values())
        _sort_groups(result_groups, request.sort, fallback_metric=metrics[0] if metrics else None)
        if len(result_groups) > request.limit:
            result_groups = result_groups[: request.limit]

        return MapStatsQueryResponse(
            filter=request.filter,
            date_range=request.date_range,
            group_by=group_by,
            metrics=metrics,
            groups=result_groups,
            pipeline=pipeline if request.include_pipeline else None,
        )

    def _aggregate_map_summaries(
        self,
        *,
        map_name: str | None,
        date_range: MapStatsDateRange,
    ) -> list[MapStatsSummary]:
        pipeline = self._summary_pipeline(map_name=map_name, date_range=date_range)
        return [MapStatsSummary.model_validate(document) for document in self.collection.aggregate(pipeline)]

    def _summary_pipeline(
        self,
        *,
        map_name: str | None,
        date_range: MapStatsDateRange,
    ) -> list[dict[str, Any]]:
        pipeline = self._base_pipeline(filter_document={}, date_range=date_range)
        if map_name is not None:
            pipeline.append({"$match": {"map_name": map_name}})
        pipeline.extend(
            [
                {
                    "$group": {
                        "_id": {
                            "map": "$map_name",
                            "matchup": {
                                "$concat": ["$student.play_race", "v", "$opponent.play_race"]
                            },
                        },
                        "games": {"$sum": 1},
                        "wins": {
                            "$sum": {
                                "$cond": [{"$eq": ["$student.result", "Win"]}, 1, 0]
                            }
                        },
                        "losses": {
                            "$sum": {
                                "$cond": [{"$eq": ["$student.result", "Loss"]}, 1, 0]
                            }
                        },
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "map": "$_id.map",
                        "matchup": "$_id.matchup",
                        "games": 1,
                        "wins": 1,
                        "losses": 1,
                        "winrate": _winrate_expression("$wins", "$games"),
                    }
                },
                {"$sort": {"map": 1, "matchup": 1}},
                {
                    "$group": {
                        "_id": "$map",
                        "games": {"$sum": "$games"},
                        "wins": {"$sum": "$wins"},
                        "losses": {"$sum": "$losses"},
                        "matchups": {
                            "$push": {
                                "matchup": "$matchup",
                                "games": "$games",
                                "wins": "$wins",
                                "losses": "$losses",
                                "winrate": "$winrate",
                            }
                        },
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "map": "$_id",
                        "games": 1,
                        "wins": 1,
                        "losses": 1,
                        "matchups": 1,
                        "winrate": _winrate_expression("$wins", "$games"),
                    }
                },
                {"$sort": {"games": -1, "map": 1}},
            ]
        )
        return pipeline

    def _grouped_query_pipeline(
        self,
        *,
        filter_document: dict[str, Any],
        date_range: MapStatsDateRange,
        group_by: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        pipeline = self._base_pipeline(filter_document=filter_document, date_range=date_range)
        pipeline.extend(
            [
                {
                    "$group": {
                        "_id": {dimension: _group_expression(dimension) for dimension in group_by},
                        "games": {"$sum": 1},
                        "wins": {
                            "$sum": {
                                "$cond": [{"$eq": ["$student.result", "Win"]}, 1, 0]
                            }
                        },
                        "losses": {
                            "$sum": {
                                "$cond": [{"$eq": ["$student.result", "Loss"]}, 1, 0]
                            }
                        },
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "key": "$_id",
                        "games": 1,
                        "wins": 1,
                        "losses": 1,
                        "winrate": _winrate_expression("$wins", "$games"),
                    }
                },
                {"$limit": limit},
            ]
        )
        return pipeline

    def _base_pipeline(
        self,
        *,
        filter_document: dict[str, Any],
        date_range: MapStatsDateRange,
    ) -> list[dict[str, Any]]:
        runtime_config = self._ensure_available()
        pipeline: list[dict[str, Any]] = [{"$match": {"players.name": runtime_config.student_name}}]
        if filter_document:
            pipeline.append({"$match": filter_document})
        date_filter = _date_filter(date_range)
        if date_filter:
            pipeline.append({"$match": {"date": date_filter}})
        pipeline.extend(
            [
                {
                    "$addFields": {
                        "student_index": {"$indexOfArray": ["$players.name", runtime_config.student_name]}
                    }
                },
                {
                    "$addFields": {
                        "student": {"$arrayElemAt": ["$players", "$student_index"]},
                        "opponent": {
                            "$arrayElemAt": [
                                "$players",
                                {
                                    "$cond": [
                                        {"$eq": ["$student_index", 0]},
                                        1,
                                        0,
                                    ]
                                },
                            ]
                        },
                    }
                },
                {"$match": {"$expr": {"$eq": ["$student.play_race", runtime_config.student_race]}}},
            ]
        )
        return pipeline

    def _ensure_available(self) -> MapStatsRuntimeConfig:
        if self._runtime_config is None:
            raise MapStatsUnavailableError(self.unavailable_reason)
        return self._runtime_config


def load_map_stats_runtime_config(
    *,
    cwd: Path | None = None,
    environ: dict[str, str] | None = None,
) -> tuple[MapStatsRuntimeConfig | None, str | None]:
    resolved_cwd = cwd or Path.cwd()
    resolved_environ = environ or dict(os.environ)
    merged: dict[str, Any] = {}

    for config_path in _sorted_config_paths(resolved_cwd):
        raw_document = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if isinstance(raw_document, dict):
            merged = _deep_merge(merged, raw_document)

    student = dict(merged.get("student") or {})
    env_name = resolved_environ.get("AICOACH_STUDENT__NAME")
    env_race = resolved_environ.get("AICOACH_STUDENT__RACE")
    env_season_start = resolved_environ.get("AICOACH_SEASON_START")
    if env_name:
        student["name"] = env_name
    if env_race:
        student["race"] = env_race
    season_start = env_season_start if env_season_start is not None else merged.get("season_start")

    try:
        return (
            MapStatsRuntimeConfig(
                student_name=student["name"],
                student_race=student["race"],
                season_start=season_start,
            ),
            None,
        )
    except (KeyError, ValidationError):
        return None, _DEFAULT_UNAVAILABLE_REASON


def _sorted_config_paths(cwd: Path) -> list[Path]:
    matches = [Path(path) for path in glob(str(cwd / "config*.yml"))]
    return sorted(matches, key=lambda path: (not path.name.startswith("."), path.name.count("."), path.name))


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(dict(merged[key]), value)
        else:
            merged[key] = value
    return merged


def _date_filter(date_range: MapStatsDateRange) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if date_range.from_date is not None:
        query["$gte"] = _coerce_utc(date_range.from_date)
    if date_range.to_date is not None:
        query["$lte"] = _coerce_utc(date_range.to_date)
    return query


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _validate_group_by(group_by: list[str]) -> list[str]:
    if not group_by:
        raise InvalidMapStatsQueryError("Map stats query must group by at least one field.")
    invalid = [field for field in group_by if field not in _ALLOWED_GROUP_BY]
    if invalid:
        raise InvalidMapStatsQueryError(
            f"Unsupported map stats grouping dimensions: {', '.join(invalid)}."
        )
    return group_by


def _validate_metrics(metrics: list[str]) -> list[str]:
    if not metrics:
        raise InvalidMapStatsQueryError("Map stats query must request at least one metric.")
    invalid = [field for field in metrics if field not in _ALLOWED_METRICS]
    if invalid:
        raise InvalidMapStatsQueryError(
            f"Unsupported map stats metrics: {', '.join(invalid)}."
        )
    return metrics


def _validate_filter(value: Any, *, path: str = "filter") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.startswith("$") and key not in _ALLOWED_FILTER_OPERATORS:
                raise InvalidMapStatsQueryError(
                    f"Unsupported map stats filter operator at {path}: {key}."
                )
            _validate_filter(nested, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_filter(nested, path=f"{path}[{index}]")


def _group_expression(dimension: str) -> Any:
    expressions: dict[str, Any] = {
        "map": "$map_name",
        "matchup": {"$concat": ["$student.play_race", "v", "$opponent.play_race"]},
        "player_race": "$student.play_race",
        "opponent_race": "$opponent.play_race",
        "result": "$student.result",
        "date_day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$date"}},
        "date_week": {
            "$dateToString": {
                "format": "%Y-%m-%d",
                "date": {"$dateTrunc": {"date": "$date", "unit": "week"}},
            }
        },
        "date_month": {
            "$dateToString": {
                "format": "%Y-%m-01",
                "date": {"$dateTrunc": {"date": "$date", "unit": "month"}},
            }
        },
    }
    return expressions[dimension]


def _winrate_expression(wins: str, games: str) -> dict[str, Any]:
    return {
        "$cond": [
            {"$gt": [games, 0]},
            {"$multiply": [{"$divide": [wins, games]}, 100]},
            0,
        ]
    }


def _project_group_result(document: dict[str, Any], *, metrics: list[str]) -> MapStatsQueryGroup:
    payload: dict[str, Any] = {"key": document["key"], "ranges": document.get("ranges")}
    for metric in _ALLOWED_METRICS:
        payload[metric] = document.get(metric) if metric in metrics else None
    return MapStatsQueryGroup.model_validate(payload)


def _group_key_token(key: dict[str, Any]) -> str:
    return json.dumps(key, default=str, sort_keys=True)


def _sort_groups(
    groups: list[MapStatsQueryGroup],
    sort_spec: dict[str, int],
    *,
    fallback_metric: str | None,
) -> None:
    if sort_spec:
        fields = list(sort_spec.items())
    elif fallback_metric is not None:
        fields = [(fallback_metric, -1)]
    else:
        fields = [("map", 1)]

    for field, direction in reversed(fields):
        reverse = direction < 0
        groups.sort(key=lambda group: _group_sort_value(group, field), reverse=reverse)


def _group_sort_value(group: MapStatsQueryGroup, field: str) -> Any:
    if field in _ALLOWED_METRICS:
        return getattr(group, field) or 0
    return group.key.get(field) or ""
