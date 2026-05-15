import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { adminApiKey, type AdminApiClient } from '../api'
import SessionDetailView from './SessionDetailView.vue'

describe('SessionDetailView', () => {
  it('loads the specialized session review with session facts, computed totals, and related conversation links', async () => {
    const sessionId = 's'.repeat(24)
    const conversationId = 'c'.repeat(24)
    const client: AdminApiClient = {
      listResources: vi.fn(),
      listSessions: vi.fn(),
      getSessionDetail: vi.fn().mockResolvedValue({
        id: sessionId,
        detail_path: `/sessions/${sessionId}`,
        session_date: '2026-05-15T10:00:00Z',
        ai_backend: 'OpenAI',
        current_conversation_id: conversationId,
        twitch_conversation_id: null,
        conversation_ids: [conversationId],
        total_input_tokens: 120,
        total_cached_tokens: 20,
        total_output_tokens: 55,
        total_tokens: 175,
        total_cost: 1.25,
      }),
      getSessionConversations: vi.fn().mockResolvedValue({
        items: [
          {
            id: conversationId,
            detail_path: `/conversations/${conversationId}`,
            trigger: 'repl',
            status: 'closed',
            item_count: 3,
            created_at: '2026-05-15T10:05:00Z',
            activity_at: '2026-05-15T10:15:00Z',
            last_item_at: '2026-05-15T10:15:00Z',
            replay_id: null,
            session_id: sessionId,
          },
        ],
        page: 1,
        page_size: 50,
        total: 1,
        total_pages: 1,
        available_statuses: ['active', 'closed', 'archived', 'failed'],
        available_triggers: ['repl', 'wake'],
      }),
      getSessionSummary: vi.fn().mockResolvedValue({
        session_id: sessionId,
        conversation_count: 1,
        item_count: 3,
        response_count: 2,
        total_input_tokens: 120,
        total_output_tokens: 55,
        total_tokens: 175,
        total_cost: 1.25,
      }),
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
        { path: '/sessions', component: { template: '<div />' } },
        { path: '/sessions/:sessionId', component: SessionDetailView },
        { path: '/conversations/:conversationId', component: { template: '<div />' } },
      ],
    })
    await router.push(`/sessions/${sessionId}`)
    await router.isReady()

    const wrapper = mount(SessionDetailView, {
      global: {
        plugins: [router],
        provide: {
          [adminApiKey as symbol]: client,
        },
      },
    })

    await flushPromises()

    expect(client.getSessionDetail).toHaveBeenCalledWith(sessionId)
    expect(client.getSessionConversations).toHaveBeenCalledWith(sessionId)
    expect(client.getSessionSummary).toHaveBeenCalledWith(sessionId)
    expect(wrapper.text()).toContain('Session review')
    expect(wrapper.text()).toContain('OpenAI')
    expect(wrapper.text()).toContain('1 conversations')
    expect(wrapper.text()).toContain('2 responses')
    expect(wrapper.text()).toContain('175')
    expect(wrapper.text()).toContain('Repl')
    expect(wrapper.find(`a[href="/conversations/${conversationId}"]`).exists()).toBe(true)
  })
})