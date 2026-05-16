import type { ApiClient, ListParams, MetadataRecord, PaginatedResponse, QueryBody } from "./types";

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