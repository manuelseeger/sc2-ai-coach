export type ConversationStatus = 'active' | 'closed' | 'archived' | 'failed'

export type ConversationTrigger =
  | 'wake'
  | 'repl'
  | 'game_start'
  | 'new_replay'
  | 'twitch_chat'
  | 'twitch_follow'
  | 'twitch_raid'
  | 'cast_replay'
  | 'replay_summary'

export interface ConversationSummary {
  id: string
  detail_path: string
  trigger: ConversationTrigger
  status: ConversationStatus
  item_count: number
  created_at: string
  activity_at: string
  last_item_at: string | null
  replay_id: string | null
  session_id: string | null
}

export interface ConversationListResponse {
  items: ConversationSummary[]
  page: number
  page_size: number
  total: number
  total_pages: number
  available_statuses: ConversationStatus[]
  available_triggers: ConversationTrigger[]
}

export type ConversationItemKind =
  | 'message'
  | 'function_call'
  | 'function_call_output'
  | 'reasoning'
  | 'summary'

export type ConversationMessageRole = 'user' | 'assistant' | 'system' | 'developer' | 'tool'

export interface ConversationReviewLink {
  id: string
  path: string
}

export interface ConversationReviewSummary {
  id: string
  detail_path: string
  trigger: ConversationTrigger
  status: ConversationStatus
  item_count: number
  created_at: string
  replay: ConversationReviewLink | null
  session: ConversationReviewLink | null
}

export interface ConversationReviewItem {
  id: string
  kind: ConversationItemKind
  created_at: string
  role: ConversationMessageRole | null
  message_text: string | null
  tool_name: string | null
  tool_arguments: Record<string, unknown> | null
  tool_output: string | null
  included_in_context: boolean
  raw_item: Record<string, unknown> | null
}

export interface ConversationDetailResponse {
  conversation: ConversationReviewSummary
  items: ConversationReviewItem[]
}

export interface ResourceDiscoveryEntry {
  name: string
  path: string
  collection: string | null
  title: string
  id_field: string
  read_only: boolean
  capabilities: string[]
  relationships: string[]
  schema_url: string | null
  available: boolean
  unavailable_reason: string | null
}