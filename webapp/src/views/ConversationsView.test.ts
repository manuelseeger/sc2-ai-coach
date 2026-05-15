import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { adminApiKey, type AdminApiClient } from '../api'
import ConversationsView from './ConversationsView.vue'

describe('ConversationsView', () => {
  it('loads the conversation inbox with active and closed statuses by default', async () => {
    const client: AdminApiClient = {
      listResources: vi.fn(),
      listConversations: vi.fn().mockResolvedValue({
        items: [
          {
            id: 'a'.repeat(24),
            detail_path: `/conversations/${'a'.repeat(24)}`,
            trigger: 'repl',
            status: 'active',
            item_count: 4,
            created_at: '2026-05-15T08:30:00Z',
            activity_at: '2026-05-15T09:15:00Z',
            last_item_at: '2026-05-15T09:15:00Z',
            replay_id: null,
            session_id: null,
          },
        ],
        page: 1,
        page_size: 20,
        total: 1,
        total_pages: 1,
        available_statuses: ['active', 'closed', 'archived', 'failed'],
        available_triggers: ['repl', 'wake'],
      }),
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
        { path: '/conversations', component: ConversationsView },
        { path: '/conversations/:conversationId', component: { template: '<div />' } },
      ],
    })
    await router.push('/conversations')
    await router.isReady()

    const wrapper = mount(ConversationsView, {
      global: {
        plugins: [router],
        provide: {
          [adminApiKey as symbol]: client,
        },
      },
    })

    await flushPromises()

    expect(client.listConversations).toHaveBeenCalledWith({
      page: 1,
      pageSize: 20,
      trigger: null,
      statuses: ['active', 'closed'],
    })
    expect(wrapper.text()).toContain('Conversations')
    expect(wrapper.text()).toContain('Repl')
    expect(wrapper.text()).toContain('Active')
    expect(wrapper.text()).toContain('4 items')
    expect(wrapper.find(`a[href="/conversations/${'a'.repeat(24)}"]`).exists()).toBe(
      true,
    )
  })
})