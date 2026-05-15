import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { adminApiKey, type AdminApiClient } from '../api'
import ConversationDetailView from './ConversationDetailView.vue'

describe('ConversationDetailView', () => {
  it('loads the deep-linked conversation review detail with sequential items', async () => {
    const conversationId = 'b'.repeat(24)
    const client: AdminApiClient = {
      listResources: vi.fn(),
      listConversations: vi.fn(),
      getConversationSummary: vi.fn(),
      getConversationDetail: vi.fn().mockResolvedValue({
        conversation: {
          id: conversationId,
          detail_path: `/conversations/${conversationId}`,
          trigger: 'repl',
          status: 'closed',
          item_count: 3,
          created_at: '2026-05-15T08:30:00Z',
          replay: { id: 'r1', path: '/replays/r1' },
          session: { id: 's1', path: '/sessions/s1' },
        },
        items: [
          {
            id: 'm1',
            kind: 'message',
            created_at: '2026-05-15T08:30:00Z',
            role: 'user',
            message_text: 'Need help with muta control.',
            tool_name: null,
            tool_arguments: null,
            tool_output: null,
            included_in_context: true,
            raw_item: null,
          },
          {
            id: 't1',
            kind: 'function_call',
            created_at: '2026-05-15T08:31:00Z',
            role: null,
            message_text: null,
            tool_name: 'load_replay',
            tool_arguments: { replay_id: 'r1' },
            tool_output: null,
            included_in_context: false,
            raw_item: null,
          },
          {
            id: 't2',
            kind: 'function_call_output',
            created_at: '2026-05-15T08:32:00Z',
            role: null,
            message_text: null,
            tool_name: 'load_replay',
            tool_arguments: null,
            tool_output: '{"units": 23}',
            included_in_context: true,
            raw_item: null,
          },
        ],
      }),
      closeConversation: vi.fn(),
      archiveConversation: vi.fn(),
      listMapStats: vi.fn(),
      getMapStatsRanges: vi.fn(),
      queryMapStats: vi.fn(),
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

    expect(client.getConversationDetail).toHaveBeenCalledWith(conversationId)
    expect(wrapper.text()).toContain('Conversation review')
    expect(wrapper.text()).toContain('Closed')
    expect(wrapper.text()).toContain('Repl')
    expect(wrapper.text()).toContain('3 items')
    expect(wrapper.text()).toContain(conversationId)
    expect(wrapper.text()).toContain('Need help with muta control.')
    expect(wrapper.text()).toContain('load_replay')
    expect(wrapper.text()).toContain('Excluded from model context')
    expect(wrapper.find('details').attributes('open')).toBeUndefined()
    expect(wrapper.find('pre').text()).toContain('{')
  })

  it('shows supported workflow actions and updates visible status from the action result', async () => {
    const conversationId = 'c'.repeat(24)
    const client: AdminApiClient = {
      listResources: vi.fn(),
      listConversations: vi.fn(),
      getConversationSummary: vi.fn(),
      getConversationDetail: vi.fn().mockResolvedValue({
        conversation: {
          id: conversationId,
          detail_path: `/conversations/${conversationId}`,
          trigger: 'repl',
          status: 'active',
          item_count: 1,
          created_at: '2026-05-15T08:30:00Z',
          replay: null,
          session: null,
        },
        items: [],
      }),
      closeConversation: vi.fn().mockResolvedValue({
        id: conversationId,
        detail_path: `/conversations/${conversationId}`,
        trigger: 'repl',
        status: 'closed',
        item_count: 1,
        created_at: '2026-05-15T08:30:00Z',
        replay: null,
        session: null,
      }),
      archiveConversation: vi.fn(),
      listMapStats: vi.fn(),
      getMapStatsRanges: vi.fn(),
      queryMapStats: vi.fn(),
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
    expect(wrapper.text()).toContain('Active')
    expect(wrapper.find('button[data-action="close"]').exists()).toBe(true)
    expect(wrapper.find('button[data-action="archive"]').exists()).toBe(true)

    await wrapper.find('button[data-action="close"]').trigger('click')
    await flushPromises()

    expect(client.closeConversation).toHaveBeenCalledWith(conversationId)
    expect(wrapper.text()).toContain('Closed')
    expect(wrapper.find('button[data-action="close"]').exists()).toBe(false)
    expect(wrapper.find('button[data-action="archive"]').exists()).toBe(true)
  })

  it('surfaces normalized action failures in the detail view', async () => {
    const conversationId = 'd'.repeat(24)
    const client: AdminApiClient = {
      listResources: vi.fn(),
      listConversations: vi.fn(),
      getConversationSummary: vi.fn(),
      getConversationDetail: vi.fn().mockResolvedValue({
        conversation: {
          id: conversationId,
          detail_path: `/conversations/${conversationId}`,
          trigger: 'repl',
          status: 'closed',
          item_count: 1,
          created_at: '2026-05-15T08:30:00Z',
          replay: null,
          session: null,
        },
        items: [],
      }),
      closeConversation: vi.fn(),
      archiveConversation: vi.fn().mockRejectedValue(new Error('Conversation is already archived.')),
      listMapStats: vi.fn(),
      getMapStatsRanges: vi.fn(),
      queryMapStats: vi.fn(),
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
    await wrapper.find('button[data-action="archive"]').trigger('click')
    await flushPromises()

    expect(client.archiveConversation).toHaveBeenCalledWith(conversationId)
    expect(wrapper.text()).toContain('Conversation is already archived.')
    expect(wrapper.text()).toContain('Closed')
  })
})