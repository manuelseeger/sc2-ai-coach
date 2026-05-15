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
})