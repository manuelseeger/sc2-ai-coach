import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { adminApiKey, type AdminApiClient } from '../api'
import ReplayDetailView from './ReplayDetailView.vue'

describe('ReplayDetailView', () => {
  it('loads replay facts, linked metadata, and participating player records', async () => {
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
      getReplayDetail: vi.fn().mockResolvedValue({
        id: replayId,
        detail_path: `/replays/${replayId}`,
        map_name: 'Site Delta LE',
        played_at: '2026-05-15T09:45:00Z',
        matchup: 'ZvZ',
        game_type: '1v1',
        real_length_seconds: 1060,
        player_count: 2,
        winning_player_name: 'zatic',
      }),
      getReplayMetadata: vi.fn().mockResolvedValue({
        replay_id: replayId,
        description: 'Aggressive muta opener into map control.',
        tags: ['muta', 'macro'],
        replay_summary_conversation: {
          id: 'c'.repeat(24),
          path: `/conversations/${'c'.repeat(24)}`,
        },
      }),
      getReplayPlayers: vi.fn().mockResolvedValue({
        replay_id: replayId,
        players: [
          {
            name: 'zatic',
            toon_handle: '2-S2-1-1515247',
            play_race: 'Zerg',
            result: 'Win',
            scaled_rating: 4182,
            avg_apm: 287.4,
            player_record: null,
            aliases: [],
          },
          {
            name: 'Driftoss',
            toon_handle: '2-S2-1-1248982',
            play_race: 'Zerg',
            result: 'Loss',
            scaled_rating: 4110,
            avg_apm: 266.1,
            player_record: {
              id: '2-S2-1-1248982',
              path: '/players/2-S2-1-1248982',
            },
            aliases: ['Driftoss'],
          },
        ],
      }),
      listMapStats: vi.fn(),
      getMapStatsRanges: vi.fn(),
      queryMapStats: vi.fn(),
    }

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div />' } },
        { path: '/conversations/:conversationId', component: { template: '<div />' } },
        { path: '/replays/:replayId', component: ReplayDetailView },
      ],
    })
    await router.push(`/replays/${replayId}`)
    await router.isReady()

    const wrapper = mount(ReplayDetailView, {
      global: {
        plugins: [router],
        provide: {
          [adminApiKey as symbol]: client,
        },
      },
    })

    await flushPromises()

    expect(client.getReplayDetail).toHaveBeenCalledWith(replayId)
    expect(client.getReplayMetadata).toHaveBeenCalledWith(replayId)
    expect(client.getReplayPlayers).toHaveBeenCalledWith(replayId)
    expect(wrapper.text()).toContain('Replay review')
    expect(wrapper.text()).toContain('Site Delta LE')
    expect(wrapper.text()).toContain('ZvZ')
    expect(wrapper.text()).toContain('Aggressive muta opener into map control.')
    expect(wrapper.text()).toContain('muta')
    expect(wrapper.text()).toContain('Driftoss')
    expect(wrapper.text()).toContain('Known player record')
    expect(wrapper.find(`a[href="/conversations/${'c'.repeat(24)}"]`).exists()).toBe(true)
    expect(wrapper.find('a[href="#player-2-S2-1-1248982"]').exists()).toBe(true)
    expect(wrapper.find('#player-2-S2-1-1248982').exists()).toBe(true)
  })
})
