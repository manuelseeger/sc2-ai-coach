from __future__ import annotations

from src.api.contracts import ResourceDiscoveryEntry


WRITABLE_RESOURCE_CAPABILITIES = [
    "list",
    "detail",
    "query",
    "create",
    "patch",
    "replace",
    "delete",
]


def discover_resources(
    *,
    map_stats_available: bool = False,
    map_stats_unavailable_reason: str | None = None,
) -> list[ResourceDiscoveryEntry]:
    return [
        ResourceDiscoveryEntry(
            name="conversations",
            path="/conversations",
            collection="ai_conversations",
            title="Conversations",
            id_field="id",
            read_only=False,
            capabilities=WRITABLE_RESOURCE_CAPABILITIES,
            relationships=["items", "responses", "session", "replay"],
            schema_url="/api/schema/conversations",
        ),
        ResourceDiscoveryEntry(
            name="sessions",
            path="/sessions",
            collection="sessions",
            title="Sessions",
            id_field="id",
            read_only=False,
            capabilities=WRITABLE_RESOURCE_CAPABILITIES,
            relationships=["conversations"],
            schema_url="/api/schema/sessions",
        ),
        ResourceDiscoveryEntry(
            name="replays",
            path="/replays",
            collection="replays",
            title="Replays",
            id_field="id",
            read_only=False,
            capabilities=WRITABLE_RESOURCE_CAPABILITIES,
            relationships=["metadata", "players"],
            schema_url="/api/schema/replays",
        ),
        ResourceDiscoveryEntry(
            name="metadata",
            path="/metadata",
            collection="meta",
            title="Metadata",
            id_field="id",
            read_only=False,
            capabilities=WRITABLE_RESOURCE_CAPABILITIES,
            relationships=["replay"],
            schema_url="/api/schema/metadata",
        ),
        ResourceDiscoveryEntry(
            name="players",
            path="/players",
            collection="players",
            title="Players",
            id_field="id",
            read_only=False,
            capabilities=WRITABLE_RESOURCE_CAPABILITIES,
            relationships=["replays", "portraits"],
            schema_url="/api/schema/players",
        ),
        ResourceDiscoveryEntry(
            name="conversation-items",
            path="/conversation-items",
            collection="ai_conversation_items",
            title="Conversation Items",
            id_field="id",
            read_only=False,
            capabilities=WRITABLE_RESOURCE_CAPABILITIES,
            relationships=["conversation"],
            schema_url="/api/schema/conversation-items",
        ),
        ResourceDiscoveryEntry(
            name="responses",
            path="/responses",
            collection="ai_responses",
            title="Responses",
            id_field="id",
            read_only=False,
            capabilities=WRITABLE_RESOURCE_CAPABILITIES,
            relationships=["conversation", "session"],
            schema_url="/api/schema/responses",
        ),
        ResourceDiscoveryEntry(
            name="map-stats",
            path="/map-stats",
            collection="replays",
            title="Map Stats",
            id_field="map_name",
            read_only=True,
            capabilities=["report"],
            relationships=[],
            schema_url=None,
            available=map_stats_available,
            unavailable_reason=(
                None if map_stats_available else map_stats_unavailable_reason
            ),
        ),
    ]
