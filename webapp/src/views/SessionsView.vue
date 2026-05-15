<template>
  <section class="page-shell">
    <header class="page-header">
      <div>
        <p class="eyebrow">Session Review</p>
        <h1>Sessions</h1>
        <p class="page-copy">Review persisted coaching sessions and open their linked conversations.</p>
      </div>
      <div class="page-meta">
        <span>{{ totalLabel }}</span>
        <span>Page {{ state.page }} of {{ state.totalPages }}</span>
      </div>
    </header>

    <p v-if="state.loading" class="panel-copy">Loading sessions…</p>
    <p v-else-if="state.error" class="panel-error">{{ state.error }}</p>
    <p v-else-if="state.items.length === 0" class="panel-copy">No sessions are available.</p>

    <ol v-else class="session-list">
      <li v-for="item in state.items" :key="item.id">
        <RouterLink :to="item.detail_path" class="session-card">
          <div class="session-card__topline">
            <span class="session-backend">{{ item.ai_backend }}</span>
            <span class="session-cost">{{ formatCurrency(item.total_cost) }}</span>
          </div>
          <h2>{{ item.id }}</h2>
          <dl class="session-facts">
            <div>
              <dt>Started</dt>
              <dd>{{ formatUtcDate(item.session_date) }}</dd>
            </div>
            <div>
              <dt>Conversations</dt>
              <dd>{{ item.conversation_count }} conversations</dd>
            </div>
            <div>
              <dt>Current</dt>
              <dd>{{ item.current_conversation_id ?? 'None' }}</dd>
            </div>
          </dl>
        </RouterLink>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import { RouterLink } from 'vue-router'

import { useAdminApi } from '../api'
import { formatUtcDate } from '../format'
import type { SessionListItem } from '../types'

const PAGE_SIZE = 20

const client = useAdminApi()

const state = reactive({
  loading: true,
  error: '',
  items: [] as SessionListItem[],
  page: 1,
  totalPages: 1,
  total: 0,
})

const totalLabel = computed(() => {
  if (state.total === 1) {
    return '1 session'
  }
  return `${state.total} sessions`
})

onMounted(async () => {
  state.loading = true
  try {
    const response = await client.listSessions({
      page: 1,
      pageSize: PAGE_SIZE,
      aiBackend: null,
      fromDate: null,
      toDate: null,
    })
    state.items = response.items
    state.page = response.page
    state.totalPages = Math.max(response.total_pages, 1)
    state.total = response.total
  } catch (error) {
    state.error = error instanceof Error ? error.message : 'Unable to load sessions.'
  } finally {
    state.loading = false
  }
})

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(value)
}
</script>

<style scoped>
.page-shell {
  display: grid;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: end;
}

.eyebrow {
  margin: 0 0 0.4rem;
  color: #8c3d1f;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: clamp(2rem, 4vw, 3rem);
}

.page-copy,
.page-meta,
.panel-copy,
.panel-error,
.session-facts dt {
  margin: 0;
  color: #52606d;
}

.page-meta {
  display: grid;
  gap: 0.25rem;
  justify-items: end;
}

.session-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 1rem;
}

.session-card {
  display: grid;
  gap: 0.9rem;
  padding: 1rem 1.1rem;
  border: 1px solid #d9cbb9;
  border-radius: 1rem;
  background: #fffaf2;
  color: inherit;
  text-decoration: none;
}

.session-card__topline,
.session-facts {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.session-backend,
.session-cost {
  display: inline-flex;
  align-items: center;
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
}

.session-backend {
  background: #f6e1bf;
  color: #7a3618;
}

.session-cost {
  background: #e9efe6;
  color: #1f2933;
}

.session-card h2 {
  margin: 0;
  font-size: 1.05rem;
}
</style>