import { describe, expect, it, vi } from 'vitest'

import { createAdminApiClient } from './api'

describe('createAdminApiClient', () => {
  it('encodes repeated status filters for the conversation inbox query', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [],
          page: 2,
          page_size: 20,
          total: 0,
          total_pages: 1,
          available_statuses: ['active', 'closed', 'archived', 'failed'],
          available_triggers: ['repl', 'wake'],
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      ),
    )

    const client = createAdminApiClient(fetchMock)

    await client.listConversations({
      page: 2,
      pageSize: 20,
      trigger: 'repl',
      statuses: ['active', 'closed'],
    })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/conversations?page=2&page_size=20&trigger=repl&status=active&status=closed',
      { headers: { Accept: 'application/json' } },
    )
  })

  it('loads the specialized conversation detail route', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          conversation: {
            id: 'a'.repeat(24),
            detail_path: `/conversations/${'a'.repeat(24)}`,
            trigger: 'repl',
            status: 'closed',
            item_count: 3,
            created_at: '2026-05-15T08:30:00Z',
            replay: { id: 'r1', path: '/replays/r1' },
            session: null,
          },
          items: [],
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      ),
    )

    const client = createAdminApiClient(fetchMock)

    await client.getConversationDetail('a'.repeat(24))

    expect(fetchMock).toHaveBeenCalledWith(
      `/api/conversations/${'a'.repeat(24)}/detail`,
      { headers: { Accept: 'application/json' } },
    )
  })

  it('posts lifecycle actions for conversation workflow controls', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'a'.repeat(24),
          detail_path: `/conversations/${'a'.repeat(24)}`,
          trigger: 'repl',
          status: 'closed',
          item_count: 3,
          created_at: '2026-05-15T08:30:00Z',
          replay: null,
          session: null,
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      ),
    )

    const client = createAdminApiClient(fetchMock)

    await client.closeConversation('a'.repeat(24))

    expect(fetchMock).toHaveBeenCalledWith(
      `/api/conversations/${'a'.repeat(24)}/close`,
      {
        method: 'POST',
        headers: { Accept: 'application/json' },
      },
    )
  })

  it('uses the shared error envelope message when a workflow action fails', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: 'invalid_action',
            message: 'Conversation is already archived.',
            details: {},
          },
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 409,
        },
      ),
    )

    const client = createAdminApiClient(fetchMock)

    await expect(client.archiveConversation('a'.repeat(24))).rejects.toThrow(
      'Conversation is already archived.',
    )
  })

  it('encodes inclusive date filters for the map-stats reporting list route', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [],
          selected_map: 'Site Delta LE',
          date_range: {
            from_date: '2026-05-01T00:00:00Z',
            to_date: '2026-05-07T23:59:59Z',
          },
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      ),
    )

    const client = createAdminApiClient(fetchMock)

    await client.listMapStats({
      map: 'Site Delta LE',
      fromDate: '2026-05-01T00:00:00Z',
      toDate: '2026-05-07T23:59:59Z',
    })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/map-stats?map=Site+Delta+LE&from_date=2026-05-01T00%3A00%3A00Z&to_date=2026-05-07T23%3A59%3A59Z',
      { headers: { Accept: 'application/json' } },
    )
  })

  it('posts the guarded map-stats aggregation query as typed JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          filter: {},
          date_range: { from_date: null, to_date: null },
          group_by: ['map', 'matchup'],
          metrics: ['games', 'wins', 'losses', 'winrate'],
          groups: [],
          pipeline: null,
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      ),
    )

    const client = createAdminApiClient(fetchMock)

    await client.queryMapStats({
      filter: { map_name: { $in: ['Site Delta LE'] } },
      date_range: {
        from_date: '2026-05-01T00:00:00Z',
        to_date: '2026-05-07T23:59:59Z',
      },
      ranges: [
        {
          name: 'season',
          from_date: '2026-05-01T00:00:00Z',
          to_date: null,
        },
      ],
      group_by: ['map', 'matchup'],
      metrics: ['games', 'wins', 'losses', 'winrate'],
      sort: { games: -1 },
      limit: 20,
      include_pipeline: false,
    })

    expect(fetchMock).toHaveBeenCalledWith('/api/map-stats/query', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        filter: { map_name: { $in: ['Site Delta LE'] } },
        date_range: {
          from_date: '2026-05-01T00:00:00Z',
          to_date: '2026-05-07T23:59:59Z',
        },
        ranges: [
          {
            name: 'season',
            from_date: '2026-05-01T00:00:00Z',
            to_date: null,
          },
        ],
        group_by: ['map', 'matchup'],
        metrics: ['games', 'wins', 'losses', 'winrate'],
        sort: { games: -1 },
        limit: 20,
        include_pipeline: false,
      }),
    })
  })
})