import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { adminApiKey, type AdminApiClient } from '../api'
import GenericResourceListView from './GenericResourceListView.vue'

function createClient(): AdminApiClient {
  return {
    listResources: vi.fn(),
    getResourceSchema: vi.fn(),
    listResource: vi.fn(),
    queryResource: vi.fn(),
    getResource: vi.fn(),
    createResource: vi.fn(),
    patchResource: vi.fn(),
    replaceResource: vi.fn(),
    deleteResource: vi.fn(),
    listSessions: vi.fn(),
    getSessionDetail: vi.fn(),
    getSessionConversations: vi.fn(),
    getSessionSummary: vi.fn(),
    listConversations: vi.fn(),
    getConversationSummary: vi.fn(),
    getConversationDetail: vi.fn(),
    closeConversation: vi.fn(),
    archiveConversation: vi.fn(),
    listPlayers: vi.fn(),
    getPlayerDetail: vi.fn(),
    getPlayerAliases: vi.fn(),
    getPlayerPortraitMetadata: vi.fn(),
    getPlayerReplays: vi.fn(),
    getReplayDetail: vi.fn(),
    getReplayMetadata: vi.fn(),
    getReplayPlayers: vi.fn(),
    listMapStats: vi.fn(),
    getMapStatsRanges: vi.fn(),
    queryMapStats: vi.fn(),
  }
}

describe('GenericResourceListView', () => {
  it('loads schema-driven maintenance data and runs guarded queries', async () => {
    const client = createClient()
    vi.mocked(client.listResources).mockResolvedValue([
      {
        name: 'metadata',
        path: '/metadata',
        collection: 'meta',
        title: 'Metadata',
        id_field: 'id',
        read_only: false,
        capabilities: ['list', 'detail', 'query', 'create', 'patch', 'replace', 'delete'],
        relationships: ['replay'],
        schema_url: '/api/schema/metadata',
        available: true,
        unavailable_reason: null,
      },
    ])
    vi.mocked(client.getResourceSchema).mockResolvedValue({
      resource: 'metadata',
      title: 'Metadata',
      id_field: 'id',
      read_only: false,
      capabilities: ['list', 'detail', 'query', 'create', 'patch', 'replace', 'delete'],
      schema: {
        title: 'Metadata',
        type: 'object',
        properties: {
          replay: { type: 'string' },
          description: { type: ['string', 'null'] },
        },
      },
      available_projections: ['table', 'detail'],
      default_projection: 'table',
    })
    vi.mocked(client.listResource).mockResolvedValue({
      resource: 'metadata',
      items: [{ id: 'm1', replay: 'a'.repeat(64), description: 'focus' }],
      page: 1,
      page_size: 20,
      total: 1,
      total_pages: 1,
      sort: '-created_at',
      projection: 'table',
      filters: {},
    })
    vi.mocked(client.queryResource).mockResolvedValue({
      resource: 'metadata',
      items: [{ id: 'm2', replay: 'b'.repeat(64), description: 'query hit' }],
      page: 1,
      page_size: 20,
      total: 1,
      total_pages: 1,
      sort: '-created_at',
      projection: 'table',
      filters: { description: { $regex: 'query' } },
    })

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/resources/:resourceName', component: GenericResourceListView }],
    })
    await router.push('/resources/metadata')
    await router.isReady()

    const wrapper = mount(GenericResourceListView, {
      global: {
        plugins: [router],
        provide: {
          [adminApiKey as symbol]: client,
        },
      },
    })

    await flushPromises()

    expect(client.listResource).toHaveBeenCalledWith('metadata', {
      page: 1,
      pageSize: 20,
      sort: '-created_at',
      projection: 'table',
      filters: {},
    })
    expect(wrapper.text()).toContain('Metadata')
    expect(wrapper.text()).toContain('Create document')
    expect(wrapper.text()).toContain('focus')

    await wrapper.get('[data-testid="query-editor"]').setValue(
      JSON.stringify({
        filter: { description: { $regex: 'query' } },
        projection: 'table',
      }),
    )
    await wrapper.get('[data-testid="run-query"]').trigger('click')
    await flushPromises()

    expect(client.queryResource).toHaveBeenCalledWith('metadata', {
      filter: { description: { $regex: 'query' } },
      projection: 'table',
    })
    expect(wrapper.text()).toContain('query hit')
  })
})
