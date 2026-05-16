export type ResourceName =
  | "replays"
  | "metadata"
  | "players"
  | "sessions"
  | "conversations"
  | "conversation-items"
  | "responses";

export interface ResourceDefinition {
  name: ResourceName;
  label: string;
  description: string;
  writable: boolean;
}

export interface AdminArea {
  id: string;
  label: string;
  description: string;
  path: string;
}

export interface HealthResponse {
  status: string;
  database: string;
  db_name: string;
}

export interface PaginatedResponse<T> {
  current_page: number;
  page_quantity: number;
  docs_quantity: number;
  docs: T[];
}

export interface SessionRecord {
  id: string;
  conversations: string[];
  current_conversation: string | null;
  twitch_conversation: string | null;
  ai_backend: string;
  session_date: string;
  completion_pricing: number;
  prompt_pricing: number;
  cached_prompt_pricing: number;
  total_input_tokens: number;
  total_cached_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cost: number;
}

export interface ConversationRecord {
  id: string;
  session: string | null;
  trigger: string;
  status: string;
  created_at: string;
  title: string | null;
  item_count: number;
  last_item_at: string | null;
  metadata: Record<string, unknown>;
}

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}

export interface ListParams {
  [key: string]: string | number | boolean | undefined;
}

export interface QueryBody {
  filter?: Record<string, unknown>;
  sort?: Record<string, 1 | -1>;
  current_page?: number;
  docs_per_page?: number;
  projection?: string;
}

export interface ApiClient {
  getHealth(): Promise<HealthResponse>;
  listResource<T>(resource: ResourceName, params?: ListParams): Promise<T>;
  queryResource<T>(resource: ResourceName, body: QueryBody): Promise<T>;
  getResource<T>(resource: ResourceName, id: string): Promise<T>;
  createResource<T>(resource: ResourceName, body: unknown): Promise<T>;
  patchResource<T>(resource: ResourceName, id: string, patch: unknown): Promise<T>;
  replaceResource<T>(resource: ResourceName, id: string, body: unknown): Promise<T>;
  deleteResource(resource: ResourceName, id: string): Promise<void>;
  getConversationItems<T>(conversationId: string, params?: ListParams): Promise<T>;
  createConversationItem<T>(conversationId: string, body: unknown): Promise<T>;
  getConversationResponses<T>(conversationId: string): Promise<T>;
  getSessionConversations<T>(sessionId: string): Promise<T>;
}