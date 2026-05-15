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