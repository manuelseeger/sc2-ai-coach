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

  it('loads the replay review routes through the shared typed client', async () => {
    const replayId = 'r'.repeat(64)
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
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
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            replay_id: replayId,
            description: 'Aggressive muta opener into map control.',
            tags: ['muta', 'macro'],
            replay_summary_conversation: {
              id: 'c'.repeat(24),
              path: `/conversations/${'c'.repeat(24)}`,
            },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            replay_id: replayId,
            players: [],
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )

    const client = createAdminApiClient(fetchMock)

    await client.getReplayDetail(replayId)
    await client.getReplayMetadata(replayId)
    await client.getReplayPlayers(replayId)

    expect(fetchMock).toHaveBeenNthCalledWith(1, `/api/replays/${replayId}`, {
      headers: { Accept: 'application/json' },
    })
    expect(fetchMock).toHaveBeenNthCalledWith(2, `/api/replays/${replayId}/metadata`, {
      headers: { Accept: 'application/json' },
    })
    expect(fetchMock).toHaveBeenNthCalledWith(3, `/api/replays/${replayId}/players`, {
      headers: { Accept: 'application/json' },
    })
  })

  it('loads the player review routes through the shared typed client', async () => {
    const toonHandle = '2-S2-1-1248982'
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [],
            page: 1,
            page_size: 20,
            total: 0,
            total_pages: 0,
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: toonHandle,
            detail_path: `/players/${toonHandle}`,
            name: 'Driftoss',
            toon_handle: toonHandle,
            alias_count: 2,
            tags: ['known-opponent'],
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            toon_handle: toonHandle,
            aliases: [],
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            toon_handle: toonHandle,
            portrait: {
              available: true,
              length: 10,
              content_type: 'image/png',
              url: `/api/players/${toonHandle}/portrait`,
            },
            portrait_constructed: {
              available: false,
              length: null,
              content_type: null,
              url: null,
            },
            aliases: [],
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            toon_handle: toonHandle,
            items: [],
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )

    const client = createAdminApiClient(fetchMock)

    await client.listPlayers({ page: 1, pageSize: 20, q: null, tag: null })
    await client.getPlayerDetail(toonHandle)
    await client.getPlayerAliases(toonHandle)
    await client.getPlayerPortraitMetadata(toonHandle)
    await client.getPlayerReplays(toonHandle)

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/players?page=1&page_size=20', {
      headers: { Accept: 'application/json' },
    })
    expect(fetchMock).toHaveBeenNthCalledWith(2, `/api/players/${toonHandle}`, {
      headers: { Accept: 'application/json' },
    })
    expect(fetchMock).toHaveBeenNthCalledWith(3, `/api/players/${toonHandle}/aliases`, {
      headers: { Accept: 'application/json' },
    })
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      `/api/players/${toonHandle}/portrait-metadata`,
      {
        headers: { Accept: 'application/json' },
      },
    )
    expect(fetchMock).toHaveBeenNthCalledWith(5, `/api/players/${toonHandle}/replays`, {
      headers: { Accept: 'application/json' },
    })
  })

  it('loads session review routes with typed detail, summary, and related conversation requests', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [],
            page: 1,
            page_size: 20,
            total: 0,
            total_pages: 0,
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: 's'.repeat(24),
            detail_path: `/sessions/${'s'.repeat(24)}`,
            session_date: '2026-05-15T10:00:00Z',
            ai_backend: 'OpenAI',
            current_conversation_id: 'c'.repeat(24),
            twitch_conversation_id: null,
            conversation_ids: ['c'.repeat(24)],
            total_input_tokens: 120,
            total_cached_tokens: 20,
            total_output_tokens: 55,
            total_tokens: 175,
            total_cost: 1.25,
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [],
            page: 1,
            page_size: 50,
            total: 0,
            total_pages: 0,
            available_statuses: ['active', 'closed', 'archived', 'failed'],
            available_triggers: ['repl', 'wake'],
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            session_id: 's'.repeat(24),
            conversation_count: 1,
            item_count: 3,
            response_count: 2,
            total_input_tokens: 120,
            total_output_tokens: 55,
            total_tokens: 175,
            total_cost: 1.25,
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )

    const client = createAdminApiClient(fetchMock)

    await client.listSessions({
      page: 1,
      pageSize: 20,
      aiBackend: 'OpenAI',
      fromDate: '2026-05-01T00:00:00Z',
      toDate: '2026-05-31T23:59:59Z',
    })
    await client.getSessionDetail('s'.repeat(24))
    await client.getSessionConversations('s'.repeat(24))
    await client.getSessionSummary('s'.repeat(24))

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/sessions?page=1&page_size=20&ai_backend=OpenAI&from_date=2026-05-01T00%3A00%3A00Z&to_date=2026-05-31T23%3A59%3A59Z',
      { headers: { Accept: 'application/json' } },
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `/api/sessions/${'s'.repeat(24)}`,
      { headers: { Accept: 'application/json' } },
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      `/api/sessions/${'s'.repeat(24)}/conversations`,
      { headers: { Accept: 'application/json' } },
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      `/api/sessions/${'s'.repeat(24)}/summary`,
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

  it('routes generic maintenance requests through the shared typed client', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            resource: 'metadata',
            title: 'Metadata',
            id_field: 'id',
            read_only: false,
            capabilities: ['list', 'detail', 'query', 'create', 'patch', 'replace', 'delete'],
            schema: {
              title: 'Metadata',
              type: 'object',
              properties: {
                replay: { type: 'string' },
                description: { type: ['string', 'null'] },
              },
            },
            available_projections: ['table', 'detail'],
            default_projection: 'table',
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            resource: 'metadata',
            items: [],
            page: 2,
            page_size: 10,
            total: 0,
            total_pages: 0,
            sort: '-created_at',
            projection: 'table',
            filters: { description: 'focus' },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            resource: 'metadata',
            items: [],
            page: 1,
            page_size: 20,
            total: 0,
            total_pages: 0,
            sort: '-created_at',
            projection: 'table',
            filters: { description: { $regex: 'focus' } },
          }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ id: 'm1', replay: 'a'.repeat(64), description: 'detail' }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ id: 'm2', replay: 'b'.repeat(64), description: 'created' }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 201,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ id: 'm2', replay: 'b'.repeat(64), description: 'patched' }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ id: 'm2', replay: 'c'.repeat(64), description: 'replaced' }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ resource: 'metadata', id: 'm2', deleted: true }),
          {
            headers: { 'Content-Type': 'application/json' },
            status: 200,
          },
        ),
      )

    const client = createAdminApiClient(fetchMock)

    await client.getResourceSchema('metadata')
    await client.listResource('metadata', {
      page: 2,
      pageSize: 10,
      sort: '-created_at',
      projection: 'table',
      filters: { description: 'focus' },
    })
    await client.queryResource('metadata', {
      filter: { description: { $regex: 'focus' } },
      sort: { created_at: -1 },
      page: 1,
      page_size: 20,
      projection: 'table',
    })
    await client.getResource('metadata', 'm1', 'detail')
    await client.createResource('metadata', {
      replay: 'b'.repeat(64),
      description: 'created',
    })
    await client.patchResource('metadata', 'm2', { description: 'patched' })
    await client.replaceResource('metadata', 'm2', {
      id: 'm2',
      replay: 'c'.repeat(64),
      description: 'replaced',
    })
    await client.deleteResource('metadata', 'm2')

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/schema/metadata', {
      headers: { Accept: 'application/json' },
    })
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/admin/resources/metadata?page=2&page_size=10&sort=-created_at&projection=table&description=focus',
      { headers: { Accept: 'application/json' } },
    )
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/admin/resources/metadata/query', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        filter: { description: { $regex: 'focus' } },
        sort: { created_at: -1 },
        page: 1,
        page_size: 20,
        projection: 'table',
      }),
    })
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      '/api/admin/resources/metadata/m1?projection=detail',
      { headers: { Accept: 'application/json' } },
    )
    expect(fetchMock).toHaveBeenNthCalledWith(5, '/api/admin/resources/metadata', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        replay: 'b'.repeat(64),
        description: 'created',
      }),
    })
    expect(fetchMock).toHaveBeenNthCalledWith(6, '/api/admin/resources/metadata/m2', {
      method: 'PATCH',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ description: 'patched' }),
    })
    expect(fetchMock).toHaveBeenNthCalledWith(7, '/api/admin/resources/metadata/m2', {
      method: 'PUT',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id: 'm2',
        replay: 'c'.repeat(64),
        description: 'replaced',
      }),
    })
    expect(fetchMock).toHaveBeenNthCalledWith(8, '/api/admin/resources/metadata/m2', {
      method: 'DELETE',
      headers: { Accept: 'application/json' },
    })
  })
})