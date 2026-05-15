import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { adminApiKey, type AdminApiClient } from '../api'
import PlayersView from './PlayersView.vue'

describe('PlayersView', () => {
  it('lists known players and links into the player review detail route', async () => {
    const toonHandle = '2-S2-1-1248982'
    const client: AdminApiClient = {
      listResources: vi.fn(),
      listSessions: vi.fn(),
      getSessionDetail: vi.fn(),
      getSessionConversations: vi.fn(),
      getSessionSummary: vi.fn(),
      listConversations: vi.fn(),
      getConversationSummary: vi.fn(),
      getConversationDetail: vi.fn(),
      closeConversation: vi.fn(),
      archiveConversation: vi.fn(),
      listPlayers: vi.fn().mockResolvedValue({
        items: [
          {
            id: toonHandle,
            detail_path: `/players/${toonHandle}`,
            name: 'Driftoss',
            toon_handle: toonHandle,
            alias_count: 2,
            last_seen_at: '2026-05-15T09:45:00Z',
            has_portrait: true,
            has_constructed_portrait: true,
          },
        ],
        page: 1,
        page_size: 20,
        total: 1,
        total_pages: 1,
      }),
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
        { path: '/players', component: PlayersView },
        { path: '/players/:toonHandle', component: { template: '<div />' } },
      ],
    })
    await router.push('/players')
    await router.isReady()

    const wrapper = mount(PlayersView, {
      global: {
        plugins: [router],
        provide: {
          [adminApiKey as symbol]: client,
        },
      },
    })

    await flushPromises()

    expect(client.listPlayers).toHaveBeenCalledWith({ page: 1, pageSize: 20, q: null, tag: null })
    expect(wrapper.text()).toContain('Known player identities')
    expect(wrapper.text()).toContain('Driftoss')
    expect(wrapper.find(`a[href="/players/${toonHandle}"]`).exists()).toBe(true)
  })
})