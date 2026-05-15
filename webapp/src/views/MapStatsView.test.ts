import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { adminApiKey, type AdminApiClient } from '../api'
import MapStatsView from './MapStatsView.vue'

describe('MapStatsView', () => {
  it('loads the specialized read-only map-stats report with filters, ranges, and grouped results', async () => {
    const client: AdminApiClient = {
      listResources: vi.fn().mockResolvedValue([
        {
          name: 'map-stats',
          path: '/map-stats',
          collection: 'replays',
          title: 'Map Stats',
          id_field: 'map_name',
          read_only: true,
          capabilities: ['report'],
          relationships: [],
          schema_url: null,
          available: true,
          unavailable_reason: null,
        },
      ]),
      listConversations: vi.fn(),
      getConversationSummary: vi.fn(),
      getConversationDetail: vi.fn(),
      closeConversation: vi.fn(),
      archiveConversation: vi.fn(),
      listMapStats: vi
        .fn()
        .mockResolvedValueOnce({
          items: [
            {
              map: 'Site Delta LE',
              games: 7,
              wins: 4,
              losses: 3,
              winrate: 57.1428571429,
              matchups: [
                {
                  matchup: 'ZvT',
                  games: 7,
                  wins: 4,
                  losses: 3,
                  winrate: 57.1428571429,
                },
              ],
            },
          ],
          selected_map: null,
          date_range: { from_date: null, to_date: null },
        })
        .mockResolvedValueOnce({
          items: [
            {
              map: 'Site Delta LE',
              games: 3,
              wins: 2,
              losses: 1,
              winrate: 66.6666666667,
              matchups: [
                {
                  matchup: 'ZvT',
                  games: 3,
                  wins: 2,
                  losses: 1,
                  winrate: 66.6666666667,
                },
              ],
            },
          ],
          selected_map: 'Site Delta LE',
          date_range: {
            from_date: '2026-05-01T00:00:00Z',
            to_date: '2026-05-07T23:59:59Z',
          },
        }),
      getMapStatsRanges: vi.fn().mockResolvedValue({
        map: 'Site Delta LE',
        ranges: [
          {
            name: 'season',
            from_date: '2026-05-01T00:00:00Z',
            to_date: null,
            stats: {
              map: 'Site Delta LE',
              games: 7,
              wins: 4,
              losses: 3,
              winrate: 57.1428571429,
              matchups: [],
            },
          },
          {
            name: 'today',
            from_date: '2026-05-07T00:00:00Z',
            to_date: null,
            stats: {
              map: 'Site Delta LE',
              games: 2,
              wins: 1,
              losses: 1,
              winrate: 50,
              matchups: [],
            },
          },
        ],
      }),
      queryMapStats: vi
        .fn()
        .mockResolvedValueOnce({
          filter: {},
          date_range: { from_date: null, to_date: null },
          group_by: ['map', 'matchup'],
          metrics: ['games', 'wins', 'losses', 'winrate'],
          groups: [
            {
              key: { map: 'Site Delta LE', matchup: 'ZvT' },
              games: 7,
              wins: 4,
              losses: 3,
              winrate: 57.1428571429,
              ranges: null,
            },
          ],
          pipeline: null,
        })
        .mockResolvedValueOnce({
          filter: { map_name: { $in: ['Site Delta LE'] } },
          date_range: {
            from_date: '2026-05-01T00:00:00Z',
            to_date: '2026-05-07T23:59:59Z',
          },
          group_by: ['map', 'matchup'],
          metrics: ['games', 'wins', 'losses', 'winrate'],
          groups: [
            {
              key: { map: 'Site Delta LE', matchup: 'ZvT' },
              games: 3,
              wins: 2,
              losses: 1,
              winrate: 66.6666666667,
              ranges: {
                season: { games: 7, wins: 4, losses: 3, winrate: 57.1428571429 },
              },
            },
          ],
          pipeline: null,
        }),
    }

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/map-stats', component: MapStatsView }],
    })
    await router.push('/map-stats')
    await router.isReady()

    const wrapper = mount(MapStatsView, {
      global: {
        plugins: [router],
        provide: {
          [adminApiKey as symbol]: client,
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Map stats')
    expect(wrapper.text()).toContain('Read-only reporting surface')
    expect(wrapper.text()).toContain('Site Delta LE')
    expect(wrapper.text()).toContain('ZvT')
    expect(client.queryMapStats).toHaveBeenCalledWith({
      filter: {},
      date_range: { from_date: null, to_date: null },
      ranges: [],
      group_by: ['map', 'matchup'],
      metrics: ['games', 'wins', 'losses', 'winrate'],
      sort: { games: -1 },
      limit: 20,
      include_pipeline: false,
    })

    await wrapper.find('select').setValue('Site Delta LE')
    await wrapper.find('input[name="from-date"]').setValue('2026-05-01')
    await wrapper.find('input[name="to-date"]').setValue('2026-05-07')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(client.listMapStats).toHaveBeenLastCalledWith({
      map: 'Site Delta LE',
      fromDate: '2026-05-01T00:00:00Z',
      toDate: '2026-05-07T23:59:59Z',
    })
    expect(client.getMapStatsRanges).toHaveBeenCalledWith('Site Delta LE', [
      { name: 'season', from_date: '2026-05-01T00:00:00Z', to_date: null },
      { name: 'today', from_date: '2026-05-07T00:00:00Z', to_date: null },
    ])
    expect(client.queryMapStats).toHaveBeenLastCalledWith({
      filter: { map_name: { $in: ['Site Delta LE'] } },
      date_range: {
        from_date: '2026-05-01T00:00:00Z',
        to_date: '2026-05-07T23:59:59Z',
      },
      ranges: [
        { name: 'season', from_date: '2026-05-01T00:00:00Z', to_date: null },
        { name: 'today', from_date: '2026-05-07T00:00:00Z', to_date: null },
      ],
      group_by: ['map', 'matchup'],
      metrics: ['games', 'wins', 'losses', 'winrate'],
      sort: { games: -1 },
      limit: 20,
      include_pipeline: false,
    })
    expect(wrapper.text()).toContain('Season')
    expect(wrapper.text()).toContain('Today')
  })

  it('surfaces an unavailable resource state without attempting reporting calls', async () => {
    const client: AdminApiClient = {
      listResources: vi.fn().mockResolvedValue([
        {
          name: 'map-stats',
          path: '/map-stats',
          collection: 'replays',
          title: 'Map Stats',
          id_field: 'map_name',
          read_only: true,
          capabilities: ['report'],
          relationships: [],
          schema_url: null,
          available: false,
          unavailable_reason: 'Map stats are unavailable in this deployment.',
        },
      ]),
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
      routes: [{ path: '/map-stats', component: MapStatsView }],
    })
    await router.push('/map-stats')
    await router.isReady()

    const wrapper = mount(MapStatsView, {
      global: {
        plugins: [router],
        provide: {
          [adminApiKey as symbol]: client,
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Unavailable')
    expect(wrapper.text()).toContain('Map stats are unavailable in this deployment.')
    expect(client.listMapStats).not.toHaveBeenCalled()
    expect(client.queryMapStats).not.toHaveBeenCalled()
  })
})