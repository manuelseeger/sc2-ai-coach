import { ApiError } from "./api";
import type {
  ApiClient,
  ListParams,
  MetadataRecord,
  PaginatedResponse,
  QueryBody,
  ReplayPlayerRelationship,
  ReplayRecord,
  ReplayWritePayload,
} from "./types";

export function loadReplayInbox(
  apiClient: ApiClient,
  params?: ListParams,
): Promise<PaginatedResponse<ReplayRecord>> {
  return apiClient.listResource<PaginatedResponse<ReplayRecord>>("replays", params);
}

export function queryReplayRecords(
  apiClient: ApiClient,
  body: QueryBody,
): Promise<PaginatedResponse<ReplayRecord>> {
  return apiClient.queryResource<PaginatedResponse<ReplayRecord>>("replays", body);
}

export async function loadReplayDetail(apiClient: ApiClient, replayId: string): Promise<{
  replay: ReplayRecord;
  metadata: MetadataRecord | null;
  players: ReplayPlayerRelationship[];
}> {
  const replayPromise = apiClient.getResource<ReplayRecord>("replays", replayId);
  const playersPromise = apiClient.getReplayPlayers<ReplayPlayerRelationship[]>(replayId);
  const metadataPromise = apiClient
    .getReplayMetadata<MetadataRecord>(replayId)
    .catch((error: unknown) => {
      if (error instanceof ApiError && error.code === "not_found") {
        return null;
      }
      throw error;
    });

  const [replay, metadata, players] = await Promise.all([
    replayPromise,
    metadataPromise,
    playersPromise,
  ]);

  return {
    replay,
    metadata,
    players,
  };
}

export function createReplayRecord(
  apiClient: ApiClient,
  body: ReplayWritePayload,
): Promise<ReplayRecord> {
  return apiClient.createResource<ReplayRecord>("replays", body);
}

export function patchReplayRecord(
  apiClient: ApiClient,
  replayId: string,
  patch: ReplayWritePayload,
): Promise<ReplayRecord> {
  return apiClient.patchResource<ReplayRecord>("replays", replayId, patch);
}

export function replaceReplayRecord(
  apiClient: ApiClient,
  replayId: string,
  body: ReplayWritePayload,
): Promise<ReplayRecord> {
  return apiClient.replaceResource<ReplayRecord>("replays", replayId, body);
}

export function deleteReplayRecord(apiClient: ApiClient, replayId: string): Promise<void> {
  return apiClient.deleteResource("replays", replayId);
}