<template>
  <section class="detail-shell">
    <p class="eyebrow">Session Review</p>
    <header v-if="state.detail" class="detail-header">
      <div>
        <h1>Session review</h1>
        <p class="detail-copy">Session facts, computed usage totals, and linked conversations.</p>
      </div>
      <RouterLink class="back-link" to="/sessions">Back to sessions</RouterLink>
    </header>

    <p v-if="state.loading" class="detail-copy">Loading session…</p>
    <p v-else-if="state.error" class="detail-error">{{ state.error }}</p>

    <article v-else-if="state.detail && state.summary" class="summary-card">
      <h2>{{ state.detail.id }}</h2>
      <dl class="summary-facts">
        <div>
          <dt>Backend</dt>
          <dd>{{ state.detail.ai_backend }}</dd>
        </div>
        <div>
          <dt>Started</dt>
          <dd>{{ formatUtcDate(state.detail.session_date) }}</dd>
        </div>
        <div>
          <dt>Current conversation</dt>
          <dd>
            <RouterLink
              v-if="state.detail.current_conversation_id"
              :to="`/conversations/${state.detail.current_conversation_id}`"
              class="context-link"
            >
              {{ state.detail.current_conversation_id }}
            </RouterLink>
            <span v-else>None</span>
          </dd>
        </div>
        <div>
          <dt>Twitch conversation</dt>
          <dd>
            <RouterLink
              v-if="state.detail.twitch_conversation_id"
              :to="`/conversations/${state.detail.twitch_conversation_id}`"
              class="context-link"
            >
              {{ state.detail.twitch_conversation_id }}
            </RouterLink>
            <span v-else>None</span>
          </dd>
        </div>
      </dl>

      <div class="summary-grid">
        <article class="metric-card">
          <span class="metric-label">Conversations</span>
          <strong>{{ state.summary.conversation_count }} conversations</strong>
        </article>
        <article class="metric-card">
          <span class="metric-label">Responses</span>
          <strong>{{ state.summary.response_count }} responses</strong>
        </article>
        <article class="metric-card">
          <span class="metric-label">Items</span>
          <strong>{{ state.summary.item_count }} items</strong>
        </article>
        <article class="metric-card">
          <span class="metric-label">Total tokens</span>
          <strong>{{ state.summary.total_tokens }}</strong>
        </article>
        <article class="metric-card">
          <span class="metric-label">Input tokens</span>
          <strong>{{ state.summary.total_input_tokens }}</strong>
        </article>
        <article class="metric-card">
          <span class="metric-label">Output tokens</span>
          <strong>{{ state.summary.total_output_tokens }}</strong>
        </article>
        <article class="metric-card metric-card--cost">
          <span class="metric-label">Total cost</span>
          <strong>{{ formatCurrency(state.summary.total_cost) }}</strong>
        </article>
      </div>
    </article>

    <section v-if="state.conversations.length > 0" class="related-section">
      <header class="related-header">
        <h2>Related conversations</h2>
        <p class="detail-copy">Follow the session-linked conversation flow without leaving the admin workspace.</p>
      </header>

      <ol class="conversation-list">
        <li v-for="item in state.conversations" :key="item.id">
          <RouterLink :to="item.detail_path" class="conversation-card">
            <div class="conversation-card__topline">
              <span class="conversation-trigger">{{ formatTrigger(item.trigger) }}</span>
              <span :class="['conversation-status', `conversation-status--${item.status}`]">
                {{ formatStatus(item.status) }}
              </span>
            </div>
            <h3>{{ item.id }}</h3>
            <dl class="conversation-facts">
              <div>
                <dt>Items</dt>
                <dd>{{ item.item_count }} items</dd>
              </div>
              <div>
                <dt>Last activity</dt>
                <dd>{{ formatUtcDate(item.activity_at) }}</dd>
              </div>
            </dl>
          </RouterLink>
        </li>
      </ol>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { useAdminApi } from '../api'
import { formatStatus, formatTrigger, formatUtcDate } from '../format'
import type { ConversationSummary, SessionDetailResponse, SessionSummaryResponse } from '../types'

const client = useAdminApi()
const route = useRoute()

const state = reactive({
  loading: true,
  error: '',
  detail: null as SessionDetailResponse | null,
  summary: null as SessionSummaryResponse | null,
  conversations: [] as ConversationSummary[],
})

onMounted(async () => {
  const sessionId = String(route.params.sessionId)
  state.loading = true
  state.error = ''

  try {
    const [detail, conversations, summary] = await Promise.all([
      client.getSessionDetail(sessionId),
      client.getSessionConversations(sessionId),
      client.getSessionSummary(sessionId),
    ])
    state.detail = detail
    state.conversations = conversations.items
    state.summary = summary
  } catch (error) {
    state.error = error instanceof Error ? error.message : 'Unable to load session.'
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
.detail-shell {
  display: grid;
  gap: 1.5rem;
}

.eyebrow {
  margin: 0;
  color: #8c3d1f;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.detail-header,
.related-header,
.conversation-card__topline,
.conversation-facts {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.detail-header {
  align-items: end;
}

.detail-copy,
.detail-error,
.summary-facts dt {
  color: #52606d;
}

.detail-error {
  color: #9b2c2c;
}

.back-link,
.context-link {
  color: #8c3d1f;
  font-weight: 700;
}

.summary-card,
.metric-card,
.conversation-card {
  border: 1px solid #d9cbb9;
  border-radius: 1rem;
}

.summary-card {
  display: grid;
  gap: 1.25rem;
  padding: 1.25rem;
  background: #fffaf2;
}

.summary-card h2,
.related-section h2,
.conversation-card h3 {
  margin: 0;
}

.summary-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.summary-facts div {
  display: grid;
  gap: 0.2rem;
}

.summary-facts dd,
.conversation-facts dd {
  margin: 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.9rem;
}

.metric-card {
  display: grid;
  gap: 0.3rem;
  padding: 0.9rem 1rem;
  background: #ffffff;
}

.metric-card--cost {
  background: #f6e1bf;
}

.metric-label {
  color: #52606d;
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
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
  gap: 0.85rem;
  padding: 1rem 1.1rem;
  background: #fffaf2;
  color: inherit;
  text-decoration: none;
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
</style>