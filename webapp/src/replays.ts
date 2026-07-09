import { ApiError } from "./api";
import type {
  ApiClient,
  ListParams,
  MetadataRecord,
  PaginatedResponse,
  QueryBody,
  ReplayInboxState,
  ReplayPlayerRelationship,
  ReplayRecord,
  ReplayWritePayload,
} from "./types";

const defaultReplayInboxState: ReplayInboxState = {
  params: {
    sort: "-date",
    current_page: 1,
    docs_per_page: 25,
  },
};

let replayInboxState: ReplayInboxState = {
  params: { ...defaultReplayInboxState.params },
};

export function getReplayInboxState(): ReplayInboxState {
  return {
    params: { ...replayInboxState.params },
  };
}

export function setReplayInboxState(state: ReplayInboxState): void {
  replayInboxState = {
    params: { ...state.params },
  };
}

export function resetReplayInboxState(): void {
  replayInboxState = {
    params: { ...defaultReplayInboxState.params },
  };
}

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
  const playersPromise = apiClient
    .getReplayPlayers<ReplayPlayerRelationship[]>(replayId)
    .catch(() => [] as ReplayPlayerRelationship[]);
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