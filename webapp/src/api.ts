import { inject, type InjectionKey } from 'vue'

import type {
  ConversationDetailResponse,
  ConversationReviewSummary,
  ConversationListResponse,
  ConversationStatus,
  ConversationSummary,
  ConversationTrigger,
  GenericResourceDeleteResponse,
  GenericResourceListResponse,
  GenericResourceQueryRequest,
  GenericResourceSchemaResponse,
  MapStatsListResponse,
  MapStatsNamedRange,
  MapStatsQueryRequest,
  MapStatsQueryResponse,
  MapStatsRangesResponse,
  PlayerAliasesResponse,
  PlayerDetailResponse,
  PlayerListResponse,
  PlayerPortraitMetadataResponse,
  PlayerRelatedReplaysResponse,
  ReplayDetailResponse,
  ReplayMetadataResponse,
  ReplayPlayersResponse,
  ResourceDiscoveryEntry,
  SessionDetailResponse,
  SessionListResponse,
  SessionSummaryResponse,
} from './types'

export interface ListConversationsParams {
  page: number
  pageSize: number
  trigger: ConversationTrigger | null
  statuses: ConversationStatus[]
}

export interface ListMapStatsParams {
  map: string | null
  fromDate: string | null
  toDate: string | null
}

export interface ListSessionsParams {
  page: number
  pageSize: number
  aiBackend: string | null
  fromDate: string | null
  toDate: string | null
}

export interface ListPlayersParams {
  page: number
  pageSize: number
  q: string | null
  tag: string | null
}

export interface ListGenericResourceParams {
  page: number
  pageSize: number
  sort: string | null
  projection: string
  filters: Record<string, unknown>
}

export interface AdminApiClient {
  listResources(): Promise<ResourceDiscoveryEntry[]>
  getResourceSchema(resource: string): Promise<GenericResourceSchemaResponse>
  listResource(resource: string, params: ListGenericResourceParams): Promise<GenericResourceListResponse>
  queryResource(resource: string, request: GenericResourceQueryRequest): Promise<GenericResourceListResponse>
  getResource(resource: string, id: string, projection?: string): Promise<Record<string, unknown>>
  createResource(resource: string, body: Record<string, unknown>): Promise<Record<string, unknown>>
  patchResource(resource: string, id: string, patch: Record<string, unknown>): Promise<Record<string, unknown>>
  replaceResource(resource: string, id: string, body: Record<string, unknown>): Promise<Record<string, unknown>>
  deleteResource(resource: string, id: string): Promise<GenericResourceDeleteResponse>
  listSessions(params: ListSessionsParams): Promise<SessionListResponse>
  getSessionDetail(sessionId: string): Promise<SessionDetailResponse>
  getSessionConversations(sessionId: string): Promise<ConversationListResponse>
  getSessionSummary(sessionId: string): Promise<SessionSummaryResponse>
  listConversations(params: ListConversationsParams): Promise<ConversationListResponse>
  getConversationSummary(conversationId: string): Promise<ConversationSummary>
  getConversationDetail(conversationId: string): Promise<ConversationDetailResponse>
  closeConversation(conversationId: string): Promise<ConversationReviewSummary>
  archiveConversation(conversationId: string): Promise<ConversationReviewSummary>
  listPlayers(params: ListPlayersParams): Promise<PlayerListResponse>
  getPlayerDetail(toonHandle: string): Promise<PlayerDetailResponse>
  getPlayerAliases(toonHandle: string): Promise<PlayerAliasesResponse>
  getPlayerPortraitMetadata(toonHandle: string): Promise<PlayerPortraitMetadataResponse>
  getPlayerReplays(toonHandle: string): Promise<PlayerRelatedReplaysResponse>
  getReplayDetail(replayId: string): Promise<ReplayDetailResponse>
  getReplayMetadata(replayId: string): Promise<ReplayMetadataResponse>
  getReplayPlayers(replayId: string): Promise<ReplayPlayersResponse>
  listMapStats(params: ListMapStatsParams): Promise<MapStatsListResponse>
  getMapStatsRanges(mapName: string, ranges: MapStatsNamedRange[]): Promise<MapStatsRangesResponse>
  queryMapStats(request: MapStatsQueryRequest): Promise<MapStatsQueryResponse>
}

export const adminApiKey: InjectionKey<AdminApiClient> = Symbol('admin-api')

interface ErrorEnvelope {
  error?: {
    message?: string
  }
  detail?: {
    error?: {
      message?: string
    }
  }
}

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

export function createAdminApiClient(fetchImpl: FetchLike = fetch): AdminApiClient {
  return {
    async listResources() {
      const payload = await requestJson<{ resources: ResourceDiscoveryEntry[] }>(
        fetchImpl,
        '/api/resources',
      )
      return payload.resources
    },

    async getResourceSchema(resource) {
      return requestJson<GenericResourceSchemaResponse>(fetchImpl, `/api/schema/${resource}`)
    },

    async listResource(resource, params) {
      const search = new URLSearchParams({
        page: String(params.page),
        page_size: String(params.pageSize),
      })
      if (params.sort !== null) {
        search.set('sort', params.sort)
      }
      search.set('projection', params.projection)
      for (const [key, value] of Object.entries(params.filters)) {
        appendSearchParam(search, key, value)
      }
      return requestJson<GenericResourceListResponse>(
        fetchImpl,
        `/api/admin/resources/${resource}?${search.toString()}`,
      )
    },

    async queryResource(resource, request) {
      return requestJson<GenericResourceListResponse>(
        fetchImpl,
        `/api/admin/resources/${resource}/query`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        },
      )
    },

    async getResource(resource, id, projection = 'detail') {
      return requestJson<Record<string, unknown>>(
        fetchImpl,
        `/api/admin/resources/${resource}/${id}?projection=${encodeURIComponent(projection)}`,
      )
    },

    async createResource(resource, body) {
      return requestJson<Record<string, unknown>>(fetchImpl, `/api/admin/resources/${resource}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })
    },

    async patchResource(resource, id, patch) {
      return requestJson<Record<string, unknown>>(fetchImpl, `/api/admin/resources/${resource}/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(patch),
      })
    },

    async replaceResource(resource, id, body) {
      return requestJson<Record<string, unknown>>(fetchImpl, `/api/admin/resources/${resource}/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })
    },

    async deleteResource(resource, id) {
      return requestJson<GenericResourceDeleteResponse>(
        fetchImpl,
        `/api/admin/resources/${resource}/${id}`,
        { method: 'DELETE' },
      )
    },

    async listSessions(params) {
      const search = new URLSearchParams({
        page: String(params.page),
        page_size: String(params.pageSize),
      })
      if (params.aiBackend !== null) {
        search.set('ai_backend', params.aiBackend)
      }
      if (params.fromDate !== null) {
        search.set('from_date', params.fromDate)
      }
      if (params.toDate !== null) {
        search.set('to_date', params.toDate)
      }
      return requestJson<SessionListResponse>(fetchImpl, `/api/sessions?${search.toString()}`)
    },

    async getSessionDetail(sessionId) {
      return requestJson<SessionDetailResponse>(fetchImpl, `/api/sessions/${sessionId}`)
    },

    async getSessionConversations(sessionId) {
      return requestJson<ConversationListResponse>(
        fetchImpl,
        `/api/sessions/${sessionId}/conversations`,
      )
    },

    async getSessionSummary(sessionId) {
      return requestJson<SessionSummaryResponse>(fetchImpl, `/api/sessions/${sessionId}/summary`)
    },

    async listConversations(params) {
      const search = new URLSearchParams({
        page: String(params.page),
        page_size: String(params.pageSize),
      })
      if (params.trigger !== null) {
        search.set('trigger', params.trigger)
      }
      for (const status of params.statuses) {
        search.append('status', status)
      }
      return requestJson<ConversationListResponse>(
        fetchImpl,
        `/api/conversations?${search.toString()}`,
      )
    },

    async getConversationSummary(conversationId) {
      return requestJson<ConversationSummary>(fetchImpl, `/api/conversations/${conversationId}`)
    },

    async getConversationDetail(conversationId) {
      return requestJson<ConversationDetailResponse>(
        fetchImpl,
        `/api/conversations/${conversationId}/detail`,
      )
    },

    async closeConversation(conversationId) {
      return requestJson<ConversationReviewSummary>(
        fetchImpl,
        `/api/conversations/${conversationId}/close`,
        { method: 'POST' },
      )
    },

    async archiveConversation(conversationId) {
      return requestJson<ConversationReviewSummary>(
        fetchImpl,
        `/api/conversations/${conversationId}/archive`,
        { method: 'POST' },
      )
    },

    async listPlayers(params) {
      const search = new URLSearchParams({
        page: String(params.page),
        page_size: String(params.pageSize),
      })
      if (params.q !== null) {
        search.set('q', params.q)
      }
      if (params.tag !== null) {
        search.set('tag', params.tag)
      }
      return requestJson<PlayerListResponse>(fetchImpl, `/api/players?${search.toString()}`)
    },

    async getPlayerDetail(toonHandle) {
      return requestJson<PlayerDetailResponse>(fetchImpl, `/api/players/${toonHandle}`)
    },

    async getPlayerAliases(toonHandle) {
      return requestJson<PlayerAliasesResponse>(fetchImpl, `/api/players/${toonHandle}/aliases`)
    },

    async getPlayerPortraitMetadata(toonHandle) {
      return requestJson<PlayerPortraitMetadataResponse>(
        fetchImpl,
        `/api/players/${toonHandle}/portrait-metadata`,
      )
    },

    async getPlayerReplays(toonHandle) {
      return requestJson<PlayerRelatedReplaysResponse>(
        fetchImpl,
        `/api/players/${toonHandle}/replays`,
      )
    },

    async getReplayDetail(replayId) {
      return requestJson<ReplayDetailResponse>(fetchImpl, `/api/replays/${replayId}`)
    },

    async getReplayMetadata(replayId) {
      return requestJson<ReplayMetadataResponse>(fetchImpl, `/api/replays/${replayId}/metadata`)
    },

    async getReplayPlayers(replayId) {
      return requestJson<ReplayPlayersResponse>(fetchImpl, `/api/replays/${replayId}/players`)
    },

    async listMapStats(params) {
      const search = new URLSearchParams()
      if (params.map !== null) {
        search.set('map', params.map)
      }
      if (params.fromDate !== null) {
        search.set('from_date', params.fromDate)
      }
      if (params.toDate !== null) {
        search.set('to_date', params.toDate)
      }
      const suffix = search.toString()
      return requestJson<MapStatsListResponse>(
        fetchImpl,
        suffix.length > 0 ? `/api/map-stats?${suffix}` : '/api/map-stats',
      )
    },

    async getMapStatsRanges(mapName, ranges) {
      const search = new URLSearchParams()
      for (const range of ranges) {
        const encoded = `${range.name}:${range.from_date}:${range.to_date ?? ''}`
        search.append('range', encoded)
      }
      return requestJson<MapStatsRangesResponse>(
        fetchImpl,
        `/api/map-stats/${encodeURIComponent(mapName)}/ranges?${search.toString()}`,
      )
    },

    async queryMapStats(request) {
      return requestJson<MapStatsQueryResponse>(fetchImpl, '/api/map-stats/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })
    },
  }
}

export function useAdminApi(): AdminApiClient {
  const client = inject(adminApiKey)
  if (client === undefined) {
    throw new Error('Admin API client was not provided.')
  }
  return client
}

async function requestJson<T>(fetchImpl: FetchLike, path: string, init?: RequestInit): Promise<T> {
  const response = await fetchImpl(path, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...init?.headers,
    },
  })
  if (!response.ok) {
    const errorEnvelope = (await response.json().catch(() => null)) as ErrorEnvelope | null
    throw new Error(
      errorEnvelope?.error?.message ??
        errorEnvelope?.detail?.error?.message ??
        `Request failed: ${response.status}`,
    )
  }
  return (await response.json()) as T
}

function appendSearchParam(search: URLSearchParams, key: string, value: unknown): void {
  if (value === null || value === undefined) {
    return
  }
  if (Array.isArray(value)) {
    for (const entry of value) {
      appendSearchParam(search, key, entry)
    }
    return
  }
  search.append(key, String(value))
}