import { inject, type InjectionKey } from 'vue'

import type {
  ConversationListResponse,
  ConversationStatus,
  ConversationSummary,
  ConversationTrigger,
  ResourceDiscoveryEntry,
} from './types'

export interface ListConversationsParams {
  page: number
  pageSize: number
  trigger: ConversationTrigger | null
  statuses: ConversationStatus[]
}

export interface AdminApiClient {
  listResources(): Promise<ResourceDiscoveryEntry[]>
  listConversations(params: ListConversationsParams): Promise<ConversationListResponse>
  getConversationSummary(conversationId: string): Promise<ConversationSummary>
}

export const adminApiKey: InjectionKey<AdminApiClient> = Symbol('admin-api')

interface ErrorEnvelope {
  error?: {
    message?: string
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
  }
}

export function useAdminApi(): AdminApiClient {
  const client = inject(adminApiKey)
  if (client === undefined) {
    throw new Error('Admin API client was not provided.')
  }
  return client
}

async function requestJson<T>(fetchImpl: FetchLike, path: string): Promise<T> {
  const response = await fetchImpl(path, { headers: { Accept: 'application/json' } })
  if (!response.ok) {
    const errorEnvelope = (await response.json().catch(() => null)) as ErrorEnvelope | null
    throw new Error(errorEnvelope?.error?.message ?? `Request failed: ${response.status}`)
  }
  return (await response.json()) as T
}