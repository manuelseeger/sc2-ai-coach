import type {
  ApiClient,
  ConversationInboxState,
  ConversationItemRecord,
  ConversationRecord,
  ListParams,
  PaginatedResponse,
  QueryBody,
} from "./types";

const defaultInboxState: ConversationInboxState = {
  params: {
    sort: "-created_at",
    current_page: 1,
    docs_per_page: 25,
  },
  selectedConversationId: null,
};

let conversationInboxState: ConversationInboxState = {
  params: { ...defaultInboxState.params },
  selectedConversationId: defaultInboxState.selectedConversationId,
};

export function loadConversationInbox(
  apiClient: ApiClient,
  params?: ListParams,
): Promise<PaginatedResponse<ConversationRecord>> {
  return apiClient.listResource<PaginatedResponse<ConversationRecord>>("conversations", params);
}

export function queryConversationRecords(
  apiClient: ApiClient,
  body: QueryBody,
): Promise<PaginatedResponse<ConversationRecord>> {
  return apiClient.queryResource<PaginatedResponse<ConversationRecord>>("conversations", body);
}

export async function loadConversationDetail(
  apiClient: ApiClient,
  conversationId: string,
): Promise<{
  conversation: ConversationRecord;
  items: ConversationItemRecord[];
}> {
  const [conversation, items] = await Promise.all([
    apiClient.getResource<ConversationRecord>("conversations", conversationId),
    apiClient.getConversationItems<ConversationItemRecord[]>(conversationId),
  ]);

  return {
    conversation,
    items,
  };
}

export function createConversationRecord(
  apiClient: ApiClient,
  body: unknown,
): Promise<ConversationRecord> {
  return apiClient.createResource<ConversationRecord>("conversations", body);
}

export function patchConversationRecord(
  apiClient: ApiClient,
  conversationId: string,
  patch: unknown,
): Promise<ConversationRecord> {
  return apiClient.patchResource<ConversationRecord>("conversations", conversationId, patch);
}

export function replaceConversationRecord(
  apiClient: ApiClient,
  conversationId: string,
  body: unknown,
): Promise<ConversationRecord> {
  return apiClient.replaceResource<ConversationRecord>("conversations", conversationId, body);
}

export function deleteConversationRecord(
  apiClient: ApiClient,
  conversationId: string,
): Promise<void> {
  return apiClient.deleteResource("conversations", conversationId);
}

export function appendConversationItem(
  apiClient: ApiClient,
  conversationId: string,
  body: unknown,
): Promise<ConversationItemRecord> {
  return apiClient.createConversationItem<ConversationItemRecord>(conversationId, body);
}

export function getConversationInboxState(): ConversationInboxState {
  return {
    params: { ...conversationInboxState.params },
    selectedConversationId: conversationInboxState.selectedConversationId,
  };
}

export function setConversationInboxState(state: ConversationInboxState): void {
  conversationInboxState = {
    params: { ...state.params },
    selectedConversationId: state.selectedConversationId,
  };
}

export function resetConversationInboxState(): void {
  conversationInboxState = {
    params: { ...defaultInboxState.params },
    selectedConversationId: defaultInboxState.selectedConversationId,
  };
}