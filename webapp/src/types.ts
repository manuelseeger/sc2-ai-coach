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

export interface SessionListItem {
  id: string
  detail_path: string
  session_date: string
  ai_backend: string
  conversation_count: number
  current_conversation_id: string | null
  total_cost: number
}

export interface SessionListResponse {
  items: SessionListItem[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface SessionDetailResponse {
  id: string
  detail_path: string
  session_date: string
  ai_backend: string
  current_conversation_id: string | null
  twitch_conversation_id: string | null
  conversation_ids: string[]
  total_input_tokens: number
  total_cached_tokens: number
  total_output_tokens: number
  total_tokens: number
  total_cost: number
}

export interface SessionSummaryResponse {
  session_id: string
  conversation_count: number
  item_count: number
  response_count: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  total_cost: number
}

export interface ReplayDetailResponse {
  id: string
  detail_path: string
  map_name: string
  played_at: string
  matchup: string
  game_type: string
  real_length_seconds: number
  player_count: number
  winning_player_name: string | null
}

export interface ReplayMetadataResponse {
  replay_id: string
  description: string | null
  tags: string[]
  replay_summary_conversation: ConversationReviewLink | null
}

export interface ReplayPlayerSummary {
  name: string
  toon_handle: string
  play_race: string
  result: string
  scaled_rating: number
  avg_apm: number
  player_record: ConversationReviewLink | null
  aliases: string[]
}

export interface ReplayPlayersResponse {
  replay_id: string
  players: ReplayPlayerSummary[]
}

export interface PlayerListItem {
  id: string
  detail_path: string
  name: string
  toon_handle: string
  alias_count: number
  last_seen_at: string | null
  has_portrait: boolean
  has_constructed_portrait: boolean
}

export interface PlayerListResponse {
  items: PlayerListItem[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface PlayerDetailResponse {
  id: string
  detail_path: string
  name: string
  toon_handle: string
  alias_count: number
  tags: string[]
}

export interface AliasPortraitAsset {
  index: number
  length: number
  content_type: string
  url: string
}

export interface PlayerAliasSummary {
  index: number
  name: string
  seen_on: string | null
  portraits: AliasPortraitAsset[]
}

export interface PlayerAliasesResponse {
  toon_handle: string
  aliases: PlayerAliasSummary[]
}

export interface PlayerPortraitAsset {
  available: boolean
  length: number | null
  content_type: string | null
  url: string | null
}

export interface PlayerPortraitMetadataResponse {
  toon_handle: string
  portrait: PlayerPortraitAsset
  portrait_constructed: PlayerPortraitAsset
  aliases: PlayerAliasSummary[]
}

export interface PlayerRelatedReplaysResponse {
  toon_handle: string
  items: ReplayDetailResponse[]
}

export interface MapStatsDateRange {
  from_date: string | null
  to_date: string | null
}

export interface MapStatsMatchupSummary {
  matchup: string
  games: number
  wins: number
  losses: number
  winrate: number
}

export interface MapStatsSummary {
  map: string
  games: number
  wins: number
  losses: number
  winrate: number
  matchups: MapStatsMatchupSummary[]
}

export interface MapStatsListResponse {
  items: MapStatsSummary[]
  selected_map: string | null
  date_range: MapStatsDateRange
}

export interface MapStatsNamedRange {
  name: string
  from_date: string
  to_date: string | null
}

export interface MapStatsRangeSummary {
  name: string
  from_date: string
  to_date: string | null
  stats: MapStatsSummary | null
}

export interface MapStatsRangesResponse {
  map: string
  ranges: MapStatsRangeSummary[]
}

export interface MapStatsMetricSummary {
  games: number
  wins: number
  losses: number
  winrate: number
}

export interface MapStatsQueryGroup {
  key: Record<string, string>
  games: number | null
  wins: number | null
  losses: number | null
  winrate: number | null
  ranges: Record<string, MapStatsMetricSummary> | null
}

export interface MapStatsQueryRequest {
  filter: Record<string, unknown>
  date_range: MapStatsDateRange
  ranges: MapStatsNamedRange[]
  group_by: string[]
  metrics: string[]
  sort: Record<string, number>
  limit: number
  include_pipeline: boolean
}

export interface MapStatsQueryResponse {
  filter: Record<string, unknown>
  date_range: MapStatsDateRange
  group_by: string[]
  metrics: string[]
  groups: MapStatsQueryGroup[]
  pipeline: Record<string, unknown>[] | null
}