import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { adminApiKey, type AdminApiClient } from '../api'
import GenericResourceDetailView from './GenericResourceDetailView.vue'

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

describe('GenericResourceDetailView', () => {
  it('creates a generic maintenance document from the dedicated new route', async () => {
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
    vi.mocked(client.createResource).mockResolvedValue({
      id: 'm2',
      replay: 'b'.repeat(64),
      description: 'created',
    })
    vi.mocked(client.getResource).mockResolvedValue({
      id: 'm2',
      replay: 'b'.repeat(64),
      description: 'created',
    })

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/resources/:resourceName', component: { template: '<div />' } },
        { path: '/resources/:resourceName/new', component: GenericResourceDetailView },
        { path: '/resources/:resourceName/:documentId', component: GenericResourceDetailView },
      ],
    })
    await router.push('/resources/metadata/new')
    await router.isReady()

    const wrapper = mount(GenericResourceDetailView, {
      global: {
        plugins: [router],
        provide: {
          [adminApiKey as symbol]: client,
        },
      },
    })

    await flushPromises()

    await wrapper.get('[data-testid="json-editor"]').setValue(
      JSON.stringify({
        replay: 'b'.repeat(64),
        description: 'created',
      }),
    )
    await wrapper.get('[data-testid="create-document"]').trigger('click')
    await flushPromises()

    expect(client.createResource).toHaveBeenCalledWith('metadata', {
      replay: 'b'.repeat(64),
      description: 'created',
    })
    expect(client.getResource).toHaveBeenCalledWith('metadata', 'm2', 'detail')
    expect(router.currentRoute.value.fullPath).toBe('/resources/metadata/m2')
  })

  it('patches and deletes a generic maintenance document through the JSON fallback', async () => {
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
    vi.mocked(client.getResource).mockResolvedValue({
      id: 'm1',
      replay: 'a'.repeat(64),
      description: 'detail',
    })
    vi.mocked(client.patchResource).mockResolvedValue({
      id: 'm1',
      replay: 'a'.repeat(64),
      description: 'patched',
    })
    vi.mocked(client.deleteResource).mockResolvedValue({
      resource: 'metadata',
      id: 'm1',
      deleted: true,
    })

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/resources/:resourceName', component: { template: '<div />' } },
        { path: '/resources/:resourceName/new', component: GenericResourceDetailView },
        { path: '/resources/:resourceName/:documentId', component: GenericResourceDetailView },
      ],
    })
    await router.push('/resources/metadata/m1')
    await router.isReady()

    const wrapper = mount(GenericResourceDetailView, {
      global: {
        plugins: [router],
        provide: {
          [adminApiKey as symbol]: client,
        },
      },
    })

    await flushPromises()

    await wrapper.get('[data-testid="json-editor"]').setValue(
      JSON.stringify({
        id: 'm1',
        replay: 'a'.repeat(64),
        description: 'patched',
      }),
    )
    await wrapper.get('[data-testid="patch-document"]').trigger('click')
    await flushPromises()

    expect(client.patchResource).toHaveBeenCalledWith('metadata', 'm1', {
      replay: 'a'.repeat(64),
      description: 'patched',
    })
    expect(wrapper.text()).toContain('Document patched.')

    await wrapper.get('[data-testid="delete-document"]').trigger('click')
    await flushPromises()

    expect(client.deleteResource).toHaveBeenCalledWith('metadata', 'm1')
    expect(router.currentRoute.value.fullPath).toBe('/resources/metadata')
  })
})
