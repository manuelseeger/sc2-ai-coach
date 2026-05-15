import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { adminApiKey, type AdminApiClient } from '../api'
import ConversationDetailView from './ConversationDetailView.vue'

describe('ConversationDetailView', () => {
  it('loads the deep-linked conversation review summary', async () => {
    const conversationId = 'b'.repeat(24)
    const client: AdminApiClient = {
      listResources: vi.fn(),
      listConversations: vi.fn(),
      getConversationSummary: vi.fn().mockResolvedValue({
        id: conversationId,
        detail_path: `/conversations/${conversationId}`,
        trigger: 'repl',
        status: 'closed',
        item_count: 7,
        created_at: '2026-05-15T08:30:00Z',
        activity_at: '2026-05-15T09:15:00Z',
        last_item_at: '2026-05-15T09:15:00Z',
        replay_id: 'r1',
        session_id: null,
      }),
    }

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/conversations', component: { template: '<div />' } },
        { path: '/conversations/:conversationId', component: ConversationDetailView },
      ],
    })
    await router.push(`/conversations/${conversationId}`)
    await router.isReady()

    const wrapper = mount(ConversationDetailView, {
      global: {
        plugins: [router],
        provide: {
          [adminApiKey as symbol]: client,
        },
      },
    })

    await flushPromises()

    expect(client.getConversationSummary).toHaveBeenCalledWith(conversationId)
    expect(wrapper.text()).toContain('Conversation review')
    expect(wrapper.text()).toContain('Closed')
    expect(wrapper.text()).toContain('Repl')
    expect(wrapper.text()).toContain('7 items')
    expect(wrapper.text()).toContain(conversationId)
  })
})