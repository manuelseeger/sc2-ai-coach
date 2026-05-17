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
  closed_at?: string | null;
  created_at: string;
  replay_id?: string | null;
  map_name?: string | null;
  opponent?: string | null;
  twitch_user?: string | null;
  handler_context?: string | null;
  title: string | null;
  item_count: number;
  last_item_at: string | null;
  metadata: Record<string, unknown>;
}

export interface ConversationContentPartRecord {
  text: string;
  type?: string;
}

export interface ConversationItemRecord {
  id: string;
  conversation: string;
  session: string | null;
  type: string;
  order: number;
  created_at: string;
  role: string | null;
  content: ConversationContentPartRecord[];
  call_id: string | null;
  name: string | null;
  arguments: Record<string, unknown> | null;
  output: string | null;
  response_id: string | null;
  response_model: string | null;
  status: string | null;
  raw_item: Record<string, unknown> | null;
  source: string | null;
  included_in_context: boolean;
  metadata: Record<string, unknown> | null;
}

export interface ConversationInboxState {
  params: ListParams;
  selectedConversationId: string | null;
}

export interface MetadataRecord {
  id: string;
  replay: string;
  description: string | null;
  tags: string[];
  replay_summary_conversation: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReplayListPlayer {
  name: string;
  toon_handle: string;
  play_race: string;
  result: string;
}

export interface PlayerInfoRecord {
  id: string;
  toon_handle: string;
  name: string;
  aliases: Array<{
    name: string;
    seen_on?: string | null;
  }>;
  tags: string[] | null;
}

export interface ReplayRecord {
  id: string;
  map_name: string;
  date: string;
  filename: string;
  region: string;
  real_length: number;
  game_type: string;
  real_type: string;
  speed: string;
  is_ladder: boolean;
  players: ReplayListPlayer[];
  [key: string]: unknown;
}

export type ReplayWritePayload = Record<string, unknown>;

export interface ReplayPlayerRelationship {
  replay_player: ReplayListPlayer;
  player_info: PlayerInfoRecord | null;
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
  getReplayMetadata<T>(replayId: string): Promise<T>;
  getReplayPlayers<T>(replayId: string): Promise<T>;
}