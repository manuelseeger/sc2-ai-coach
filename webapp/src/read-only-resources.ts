import type {
  ApiClient,
  ConversationItemRecord,
  ListParams,
  PaginatedResponse,
  QueryBody,
  ResourceName,
  ResponseRecord,
  SessionRecord,
} from "./types";

export type ReadOnlyResourceName = "conversation-items" | "responses" | "sessions";

export type ReadOnlyResourceRecord = ConversationItemRecord | ResponseRecord | SessionRecord;

export function loadReadOnlyResourceInbox(
  apiClient: ApiClient,
  resource: ReadOnlyResourceName,
  params?: ListParams,
): Promise<PaginatedResponse<ReadOnlyResourceRecord>> {
  return apiClient.listResource<PaginatedResponse<ReadOnlyResourceRecord>>(resource, params);
}

export function queryReadOnlyResourceRecords(
  apiClient: ApiClient,
  resource: ReadOnlyResourceName,
  body: QueryBody,
): Promise<PaginatedResponse<ReadOnlyResourceRecord>> {
  return apiClient.queryResource<PaginatedResponse<ReadOnlyResourceRecord>>(resource, body);
}

export function loadReadOnlyResourceDetail(
  apiClient: ApiClient,
  resource: ReadOnlyResourceName,
  recordId: string,
): Promise<ReadOnlyResourceRecord> {
  return apiClient.getResource<ReadOnlyResourceRecord>(resource as ResourceName, recordId);
}

export function lookupResponseRecord(
  apiClient: ApiClient,
  responseId: string,
): Promise<ResponseRecord> {
  return apiClient.getResponseByResponseId<ResponseRecord>(responseId);
}