import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { adminApiKey, type AdminApiClient } from '../api'
import PlayerDetailView from './PlayerDetailView.vue'

describe('PlayerDetailView', () => {
  it('loads portrait metadata, aliases, and related replays for a player review route', async () => {
    const toonHandle = '2-S2-1-1248982'
    const replayId = 'r'.repeat(64)
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
      listPlayers: vi.fn(),
      getPlayerDetail: vi.fn().mockResolvedValue({
        id: toonHandle,
        detail_path: `/players/${toonHandle}`,
        name: 'Driftoss',
        toon_handle: toonHandle,
        alias_count: 2,
        tags: ['known-opponent'],
      }),
      getPlayerAliases: vi.fn().mockResolvedValue({
        toon_handle: toonHandle,
        aliases: [
          {
            index: 0,
            name: 'Driftoss',
            seen_on: '2026-05-15T09:45:00Z',
            portraits: [
              {
                index: 0,
                length: 12,
                content_type: 'image/png',
                url: `/api/players/${toonHandle}/aliases/0/portraits/0`,
              },
            ],
          },
        ],
      }),
      getPlayerPortraitMetadata: vi.fn().mockResolvedValue({
        toon_handle: toonHandle,
        portrait: {
          available: true,
          length: 12,
          content_type: 'image/png',
          url: `/api/players/${toonHandle}/portrait`,
        },
        portrait_constructed: {
          available: true,
          length: 12,
          content_type: 'image/png',
          url: `/api/players/${toonHandle}/portrait/constructed`,
        },
        aliases: [],
      }),
      getPlayerReplays: vi.fn().mockResolvedValue({
        toon_handle: toonHandle,
        items: [
          {
            id: replayId,
            detail_path: `/replays/${replayId}`,
            map_name: 'Site Delta LE',
            played_at: '2026-05-15T09:45:00Z',
            matchup: 'ZvZ',
            game_type: '1v1',
            real_length_seconds: 1060,
            player_count: 2,
            winning_player_name: 'zatic',
          },
        ],
      }),
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
        { path: '/players', component: { template: '<div />' } },
        { path: '/players/:toonHandle', component: PlayerDetailView },
        { path: '/replays/:replayId', component: { template: '<div />' } },
      ],
    })
    await router.push(`/players/${toonHandle}`)
    await router.isReady()

    const wrapper = mount(PlayerDetailView, {
      global: {
        plugins: [router],
        provide: {
          [adminApiKey as symbol]: client,
        },
      },
    })

    await flushPromises()

    expect(client.getPlayerDetail).toHaveBeenCalledWith(toonHandle)
    expect(client.getPlayerAliases).toHaveBeenCalledWith(toonHandle)
    expect(client.getPlayerPortraitMetadata).toHaveBeenCalledWith(toonHandle)
    expect(client.getPlayerReplays).toHaveBeenCalledWith(toonHandle)
    expect(wrapper.text()).toContain('Canonical player identity')
    expect(wrapper.text()).toContain('known-opponent')
    expect(wrapper.text()).toContain('Portrait media')
    expect(wrapper.text()).toContain('Related replays')
    expect(wrapper.find(`img[src="/api/players/${toonHandle}/portrait"]`).exists()).toBe(true)
    expect(
      wrapper.find(`img[src="/api/players/${toonHandle}/aliases/0/portraits/0"]`).exists(),
    ).toBe(true)
    expect(wrapper.find(`a[href="/replays/${replayId}"]`).exists()).toBe(true)
  })
})