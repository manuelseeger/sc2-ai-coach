import type {
  ApiClient,
  ListParams,
  MetadataInboxState,
  MetadataRecord,
  PaginatedResponse,
  QueryBody,
} from "./types";

const defaultMetadataInboxState: MetadataInboxState = {
  params: {
    sort: "-updated_at",
    current_page: 1,
    docs_per_page: 25,
  },
};

let metadataInboxState: MetadataInboxState = {
  params: { ...defaultMetadataInboxState.params },
};

export function getMetadataInboxState(): MetadataInboxState {
  return {
    params: { ...metadataInboxState.params },
  };
}

export function setMetadataInboxState(state: MetadataInboxState): void {
  metadataInboxState = {
    params: { ...state.params },
  };
}

export function resetMetadataInboxState(): void {
  metadataInboxState = {
    params: { ...defaultMetadataInboxState.params },
  };
}

export function loadMetadataInbox(
  apiClient: ApiClient,
  params?: ListParams,
): Promise<PaginatedResponse<MetadataRecord>> {
  return apiClient.listResource<PaginatedResponse<MetadataRecord>>("metadata", params);
}

export function queryMetadataRecords(
  apiClient: ApiClient,
  body: QueryBody,
): Promise<PaginatedResponse<MetadataRecord>> {
  return apiClient.queryResource<PaginatedResponse<MetadataRecord>>("metadata", body);
}

export function loadMetadataDetail(
  apiClient: ApiClient,
  metadataId: string,
): Promise<MetadataRecord> {
  return apiClient.getResource<MetadataRecord>("metadata", metadataId);
}

export function createMetadataRecord(
  apiClient: ApiClient,
  body: unknown,
): Promise<MetadataRecord> {
  return apiClient.createResource<MetadataRecord>("metadata", body);
}

export function patchMetadataRecord(
  apiClient: ApiClient,
  metadataId: string,
  patch: unknown,
): Promise<MetadataRecord> {
  return apiClient.patchResource<MetadataRecord>("metadata", metadataId, patch);
}

export function replaceMetadataRecord(
  apiClient: ApiClient,
  metadataId: string,
  body: unknown,
): Promise<MetadataRecord> {
  return apiClient.replaceResource<MetadataRecord>("metadata", metadataId, body);
}

export function deleteMetadataRecord(apiClient: ApiClient, metadataId: string): Promise<void> {
  return apiClient.deleteResource("metadata", metadataId);
}