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
})