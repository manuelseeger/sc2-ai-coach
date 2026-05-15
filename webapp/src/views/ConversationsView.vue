<template>
  <section class="page-shell">
    <header class="page-header">
      <div>
        <p class="eyebrow">Conversation Inbox</p>
        <h1>Conversations</h1>
        <p class="page-copy">
          Recent-first conversation review across active and closed sessions.
        </p>
      </div>
      <div class="page-meta">
        <span>{{ totalLabel }}</span>
        <span>Page {{ state.page }} of {{ state.totalPages }}</span>
      </div>
    </header>

    <form class="filters" @submit.prevent="reload(1)">
      <label class="filter-control">
        <span>Trigger</span>
        <select v-model="state.trigger">
          <option :value="ALL_TRIGGERS">All triggers</option>
          <option v-for="trigger in availableTriggers" :key="trigger" :value="trigger">
            {{ formatTrigger(trigger) }}
          </option>
        </select>
      </label>

      <fieldset class="status-group">
        <legend>Status</legend>
        <label v-for="status in availableStatuses" :key="status" class="status-option">
          <input
            :checked="state.statuses.includes(status)"
            type="checkbox"
            @change="toggleStatus(status)"
          >
          <span>{{ formatStatus(status) }}</span>
        </label>
      </fieldset>

      <button class="action-button" type="submit">Apply filters</button>
    </form>

    <p v-if="state.loading" class="panel-copy">Loading conversations…</p>
    <p v-else-if="state.error" class="panel-error">{{ state.error }}</p>
    <p v-else-if="state.items.length === 0" class="panel-copy">
      No conversations match the current inbox filters.
    </p>

    <ol v-else class="conversation-list">
      <li v-for="item in state.items" :key="item.id">
        <RouterLink :to="item.detail_path" class="conversation-card">
          <div class="conversation-card__topline">
            <span class="conversation-trigger">{{ formatTrigger(item.trigger) }}</span>
            <span :class="['conversation-status', `conversation-status--${item.status}`]">
              {{ formatStatus(item.status) }}
            </span>
          </div>
          <h2>{{ item.id }}</h2>
          <dl class="conversation-facts">
            <div>
              <dt>Items</dt>
              <dd>{{ item.item_count }} items</dd>
            </div>
            <div>
              <dt>Last activity</dt>
              <dd>{{ formatDate(item.activity_at) }}</dd>
            </div>
            <div>
              <dt>Context</dt>
              <dd>{{ relationshipLabel(item) }}</dd>
            </div>
          </dl>
        </RouterLink>
      </li>
    </ol>

    <nav class="pagination" aria-label="Conversation pages">
      <button
        class="action-button action-button--ghost"
        type="button"
        :disabled="state.loading || state.page <= 1"
        @click="reload(state.page - 1)"
      >
        Previous
      </button>
      <button
        class="action-button action-button--ghost"
        type="button"
        :disabled="state.loading || state.page >= state.totalPages"
        @click="reload(state.page + 1)"
      >
        Next
      </button>
    </nav>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import { RouterLink } from 'vue-router'

import { useAdminApi } from '../api'
import { formatStatus, formatTrigger, formatUtcDate } from '../format'
import type { ConversationStatus, ConversationSummary, ConversationTrigger } from '../types'

const ALL_TRIGGERS = ''
const DEFAULT_STATUSES: ConversationStatus[] = ['active', 'closed']
const PAGE_SIZE = 20

const client = useAdminApi()

const state = reactive({
  loading: true,
  error: '',
  items: [] as ConversationSummary[],
  page: 1,
  totalPages: 1,
  total: 0,
  trigger: ALL_TRIGGERS,
  statuses: [...DEFAULT_STATUSES] as ConversationStatus[],
  availableStatuses: [...DEFAULT_STATUSES] as ConversationStatus[],
  availableTriggers: [] as ConversationTrigger[],
})

const totalLabel = computed(() => {
  if (state.total === 1) {
    return '1 conversation'
  }
  return `${state.total} conversations`
})

const availableStatuses = computed(() => state.availableStatuses)
const availableTriggers = computed(() => state.availableTriggers)

onMounted(async () => {
  await reload(1)
})

async function reload(page: number): Promise<void> {
  state.loading = true
  state.error = ''

  try {
    const response = await client.listConversations({
      page,
      pageSize: PAGE_SIZE,
      trigger: state.trigger === ALL_TRIGGERS ? null : state.trigger,
      statuses: [...state.statuses],
    })

    state.items = response.items
    state.page = response.page
    state.totalPages = Math.max(response.total_pages, 1)
    state.total = response.total
    state.availableStatuses = response.available_statuses
    state.availableTriggers = response.available_triggers
  } catch (error) {
    state.error = error instanceof Error ? error.message : 'Unable to load conversations.'
  } finally {
    state.loading = false
  }
}

function toggleStatus(status: ConversationStatus): void {
  if (state.statuses.includes(status)) {
    if (state.statuses.length === 1) {
      return
    }
    state.statuses = state.statuses.filter((candidate) => candidate !== status)
    return
  }

  state.statuses = [...state.statuses, status]
}

function relationshipLabel(item: ConversationSummary): string {
  const labels: string[] = []
  if (item.replay_id !== null) {
    labels.push('Replay linked')
  }
  if (item.session_id !== null) {
    labels.push('Session linked')
  }
  if (labels.length === 0) {
    return 'Standalone'
  }
  return labels.join(' · ')
}

function formatDate(value: string): string {
  return formatUtcDate(value)
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
.panel-copy,
.panel-error,
.page-meta {
  margin: 0;
  color: #52606d;
}

.page-meta {
  display: grid;
  gap: 0.25rem;
  justify-items: end;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid #d9cbb9;
  border-radius: 1rem;
  background: rgba(255, 250, 242, 0.85);
}

.filter-control,
.status-group {
  display: grid;
  gap: 0.5rem;
}

.filter-control span,
.status-group legend {
  font-size: 0.9rem;
  font-weight: 700;
}

.filter-control select {
  min-width: 14rem;
  padding: 0.7rem 0.8rem;
  border: 1px solid #d9cbb9;
  border-radius: 0.7rem;
  background: #fffaf2;
}

.status-group {
  border: 0;
  padding: 0;
  margin: 0;
}

.status-option {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-right: 0.75rem;
}

.action-button {
  align-self: end;
  padding: 0.75rem 1rem;
  border: 0;
  border-radius: 999px;
  background: #8c3d1f;
  color: #fffaf2;
  font: inherit;
  cursor: pointer;
}

.action-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.action-button--ghost {
  background: #fffaf2;
  border: 1px solid #d9cbb9;
  color: #1f2933;
}

.conversation-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 1rem;
}

.conversation-card {
  display: grid;
  gap: 0.9rem;
  padding: 1rem 1.1rem;
  border: 1px solid #d9cbb9;
  border-radius: 1rem;
  background: #fffaf2;
  color: inherit;
  text-decoration: none;
}

.conversation-card__topline,
.conversation-facts,
.pagination {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.conversation-trigger,
.conversation-status {
  display: inline-flex;
  align-items: center;
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
}

.conversation-trigger {
  background: #f6e1bf;
  color: #7a3618;
}

.conversation-status {
  background: #e9efe6;
}

.conversation-status--closed {
  background: #e8e1f3;
}

.conversation-status--archived,
.conversation-status--failed {
  background: #f8d8d8;
}

.conversation-card h2 {
  margin: 0;
  font-size: 1.05rem;
}

.conversation-facts {
  flex-wrap: wrap;
  margin: 0;
}

.conversation-facts div {
  display: grid;
  gap: 0.2rem;
}

.conversation-facts dt {
  color: #52606d;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.conversation-facts dd {
  margin: 0;
}

@media (max-width: 720px) {
  .page-header,
  .conversation-card__topline,
  .conversation-facts,
  .pagination {
    flex-direction: column;
    align-items: stretch;
  }

  .page-meta {
    justify-items: start;
  }
}
</style>