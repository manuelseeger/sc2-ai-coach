import type {
  ApiClient,
  BulkPlayerPortraitMetadataRecord,
  ListParams,
  PaginatedResponse,
  PlayerAliasRecord,
  PlayerInfoRecord,
  PlayerPortraitMetadataRecord,
  QueryBody,
  ReplayRecord,
} from "./types";

export function loadPlayerInbox(
  apiClient: ApiClient,
  params?: ListParams,
): Promise<PaginatedResponse<PlayerInfoRecord>> {
  return apiClient.listResource<PaginatedResponse<PlayerInfoRecord>>("players", params);
}

export function queryPlayerRecords(
  apiClient: ApiClient,
  body: QueryBody,
): Promise<PaginatedResponse<PlayerInfoRecord>> {
  return apiClient.queryResource<PaginatedResponse<PlayerInfoRecord>>("players", body);
}

export function loadPlayerResourceDetail(
  apiClient: ApiClient,
  toonHandle: string,
): Promise<PlayerInfoRecord> {
  return apiClient.getResource<PlayerInfoRecord>("players", toonHandle);
}

export async function loadPlayerDetail(
  apiClient: ApiClient,
  toonHandle: string,
): Promise<{
  player: PlayerInfoRecord;
  aliases: PlayerAliasRecord[];
  portraitMetadata: PlayerPortraitMetadataRecord;
  replays: PaginatedResponse<ReplayRecord>;
}> {
  const [player, aliases, portraitMetadata, replays] = await Promise.all([
    apiClient.getResource<PlayerInfoRecord>("players", toonHandle),
    apiClient.getPlayerAliases<PlayerAliasRecord[]>(toonHandle),
    apiClient.getPlayerPortraitMetadata<PlayerPortraitMetadataRecord>(toonHandle),
    apiClient.getPlayerReplays<PaginatedResponse<ReplayRecord>>(toonHandle, {
      docs_per_page: 20,
    }),
  ]);

  return {
    player,
    aliases,
    portraitMetadata,
    replays,
  };
}

export async function loadPlayerPortraitMetadataMap(
  apiClient: ApiClient,
  toonHandles: string[],
): Promise<Record<string, PlayerPortraitMetadataRecord>> {
  if (toonHandles.length === 0) {
    return {};
  }

  const payload = await apiClient.getPlayersPortraitMetadata<BulkPlayerPortraitMetadataRecord>(
    toonHandles,
  );

  return Object.fromEntries(payload.items.map((item) => [item.toon_handle, item]));
}

export function createPlayerRecord(
  apiClient: ApiClient,
  body: unknown,
): Promise<PlayerInfoRecord> {
  return apiClient.createResource<PlayerInfoRecord>("players", body);
}

export function patchPlayerRecord(
  apiClient: ApiClient,
  toonHandle: string,
  patch: unknown,
): Promise<PlayerInfoRecord> {
  return apiClient.patchResource<PlayerInfoRecord>("players", toonHandle, patch);
}

export function replacePlayerRecord(
  apiClient: ApiClient,
  toonHandle: string,
  body: unknown,
): Promise<PlayerInfoRecord> {
  return apiClient.replaceResource<PlayerInfoRecord>("players", toonHandle, body);
}

export function deletePlayerRecord(
  apiClient: ApiClient,
  toonHandle: string,
): Promise<void> {
  return apiClient.deleteResource("players", toonHandle);
}