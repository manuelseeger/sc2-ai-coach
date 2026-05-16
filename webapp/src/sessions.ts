import type {
  ApiClient,
  ConversationRecord,
  PaginatedResponse,
  SessionRecord,
} from "./types";

export function loadSessionInbox(
  apiClient: ApiClient,
): Promise<PaginatedResponse<SessionRecord>> {
  return apiClient.listResource<PaginatedResponse<SessionRecord>>("sessions");
}

export async function loadSessionDetail(apiClient: ApiClient, sessionId: string): Promise<{
  session: SessionRecord;
  conversations: ConversationRecord[];
}> {
  const [session, conversations] = await Promise.all([
    apiClient.getResource<SessionRecord>("sessions", sessionId),
    apiClient.getSessionConversations<ConversationRecord[]>(sessionId),
  ]);

  return {
    session,
    conversations,
  };
}