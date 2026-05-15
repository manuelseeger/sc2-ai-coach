import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { adminApiKey, type AdminApiClient } from '../api'
import WorkspaceView from './WorkspaceView.vue'

describe('WorkspaceView', () => {
  it('routes the discovered sessions resource into the session review workflow', async () => {
    const client: AdminApiClient = {
      listResources: vi.fn().mockResolvedValue([
        {
          name: 'sessions',
          path: '/sessions',
          collection: 'sessions',
          title: 'Sessions',
          id_field: 'id',
          read_only: false,
          capabilities: ['list', 'detail'],
          relationships: ['conversations'],
          schema_url: '/api/schema/sessions',
          available: true,
          unavailable_reason: null,
        },
      ]),
      listSessions: vi.fn(),
      getSessionDetail: vi.fn(),
      getSessionConversations: vi.fn(),
      getSessionSummary: vi.fn(),
      listConversations: vi.fn(),
      getConversationSummary: vi.fn(),
      getConversationDetail: vi.fn(),
      closeConversation: vi.fn(),
      archiveConversation: vi.fn(),
      listMapStats: vi.fn(),
      getMapStatsRanges: vi.fn(),
      queryMapStats: vi.fn(),
    }

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: WorkspaceView },
        { path: '/sessions', component: { template: '<div />' } },
      ],
    })
    await router.push('/')
    await router.isReady()

    const wrapper = mount(WorkspaceView, {
      global: {
        plugins: [router],
        provide: {
          [adminApiKey as symbol]: client,
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Sessions')
    expect(wrapper.text()).toContain('Open session review')
    expect(wrapper.find('a[href="/sessions"]').exists()).toBe(true)
  })
})