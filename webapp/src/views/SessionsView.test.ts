import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { adminApiKey, type AdminApiClient } from '../api'
import SessionsView from './SessionsView.vue'

describe('SessionsView', () => {
  it('loads the session review inbox and links each session into the specialized detail flow', async () => {
    const sessionId = 's'.repeat(24)
    const client: AdminApiClient = {
      listResources: vi.fn(),
      listSessions: vi.fn().mockResolvedValue({
        items: [
          {
            id: sessionId,
            detail_path: `/sessions/${sessionId}`,
            session_date: '2026-05-15T10:00:00Z',
            ai_backend: 'OpenAI',
            conversation_count: 2,
            current_conversation_id: 'c'.repeat(24),
            total_cost: 1.25,
          },
        ],
        page: 1,
        page_size: 20,
        total: 1,
        total_pages: 1,
      }),
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

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/sessions', component: SessionsView },
        { path: '/sessions/:sessionId', component: { template: '<div />' } },
      ],
    })
    await router.push('/sessions')
    await router.isReady()

    const wrapper = mount(SessionsView, {
      global: {
        plugins: [router],
        provide: {
          [adminApiKey as symbol]: client,
        },
      },
    })

    await flushPromises()

    expect(client.listSessions).toHaveBeenCalledWith({
      page: 1,
      pageSize: 20,
      aiBackend: null,
      fromDate: null,
      toDate: null,
    })
    expect(wrapper.text()).toContain('Sessions')
    expect(wrapper.text()).toContain('OpenAI')
    expect(wrapper.text()).toContain('2 conversations')
    expect(wrapper.find(`a[href="/sessions/${sessionId}"]`).exists()).toBe(true)
  })
})