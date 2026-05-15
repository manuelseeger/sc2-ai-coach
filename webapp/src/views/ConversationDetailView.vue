<template>
  <section class="detail-shell">
    <p class="eyebrow">Conversation Review</p>
    <header v-if="detail" class="detail-header">
      <div>
        <h1>Conversation review</h1>
        <p class="detail-copy">
          Complete persisted conversation flow in authoritative backend order.
        </p>
      </div>
      <RouterLink class="back-link" to="/conversations">Back to inbox</RouterLink>
    </header>

    <p v-if="loading" class="detail-copy">Loading conversation…</p>
    <p v-else-if="error" class="detail-error">{{ error }}</p>

    <article v-else-if="detail" class="summary-card">
      <h2>{{ detail.conversation.id }}</h2>
      <dl class="summary-facts">
        <div>
          <dt>Trigger</dt>
          <dd>{{ formatTrigger(detail.conversation.trigger) }}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{{ formatStatus(detail.conversation.status) }}</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{{ formatUtcDate(detail.conversation.created_at) }}</dd>
        </div>
        <div>
          <dt>Items</dt>
          <dd>{{ detail.conversation.item_count }} items</dd>
        </div>
        <div>
          <dt>Replay</dt>
          <dd>
            <RouterLink
              v-if="detail.conversation.replay"
              :to="detail.conversation.replay.path"
              class="context-link"
            >
              {{ detail.conversation.replay.id }}
            </RouterLink>
            <span v-else>None</span>
          </dd>
        </div>
        <div>
          <dt>Session</dt>
          <dd>
            <RouterLink
              v-if="detail.conversation.session"
              :to="detail.conversation.session.path"
              class="context-link"
            >
              {{ detail.conversation.session.id }}
            </RouterLink>
            <span v-else>None</span>
          </dd>
        </div>
      </dl>
    </article>

    <ol v-if="detail" class="item-list">
      <li v-for="item in detail.items" :key="item.id">
        <article :class="['item-card', `item-card--${item.kind}`]">
          <header class="item-card__header">
            <div class="item-card__titleline">
              <span class="item-kind">{{ itemKindLabel(item.kind) }}</span>
              <span v-if="item.role" class="item-role">{{ item.role }}</span>
              <strong v-if="item.tool_name" class="item-tool-name">{{ item.tool_name }}</strong>
              <span v-if="!item.included_in_context" class="context-marker">
                Excluded from model context
              </span>
            </div>
            <time :datetime="item.created_at" class="item-timestamp">
              {{ formatUtcDate(item.created_at) }}
            </time>
          </header>

          <p v-if="item.message_text" :class="['message-text', { 'message-text--code': isCodeLike(item.message_text) }]">
            {{ item.message_text }}
          </p>

          <details v-if="item.tool_arguments" class="payload-panel">
            <summary>View raw arguments</summary>
            <pre>{{ formatPayload(item.tool_arguments) }}</pre>
          </details>

          <details v-if="item.tool_output" class="payload-panel">
            <summary>View raw result</summary>
            <pre>{{ item.tool_output }}</pre>
          </details>
        </article>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { useAdminApi } from '../api'
import { formatStatus, formatTrigger, formatUtcDate } from '../format'
import type { ConversationDetailResponse, ConversationItemKind } from '../types'

const client = useAdminApi()
const route = useRoute()

const loading = ref(true)
const error = ref('')
const detail = ref<ConversationDetailResponse | null>(null)

onMounted(async () => {
  try {
    detail.value = await client.getConversationDetail(String(route.params.conversationId))
  } catch (loadError) {
    error.value = loadError instanceof Error ? loadError.message : 'Unable to load conversation.'
  } finally {
    loading.value = false
  }
})

function itemKindLabel(kind: ConversationItemKind): string {
  switch (kind) {
    case 'function_call':
      return 'Tool call'
    case 'function_call_output':
      return 'Tool result'
    default:
      return kind.charAt(0).toUpperCase() + kind.slice(1)
  }
}

function formatPayload(payload: Record<string, unknown>): string {
  return JSON.stringify(payload, null, 2)
}

function isCodeLike(text: string): boolean {
  return text.includes('{') || text.includes('```') || text.includes('def ') || text.includes('const ')
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

.detail-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: end;
}

.detail-header h1,
.summary-card h2 {
  margin: 0;
}

.detail-copy,
.detail-error,
.summary-facts dt {
  color: #52606d;
}

.detail-error {
  color: #9b2c2c;
}

.back-link {
  color: #8c3d1f;
  font-weight: 700;
}

.context-link {
  color: #8c3d1f;
  font-weight: 600;
}

.summary-card {
  padding: 1.25rem;
  border: 1px solid #d9cbb9;
  border-radius: 1rem;
  background: #fffaf2;
}

.summary-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.summary-facts div {
  display: grid;
  gap: 0.2rem;
}

.summary-facts dd {
  margin: 0;
}

.item-list {
  display: grid;
  gap: 1rem;
  padding: 0;
  margin: 0;
  list-style: none;
}

.item-card {
  display: grid;
  gap: 0.85rem;
  padding: 1rem 1.1rem;
  border-radius: 1rem;
  border: 1px solid #d9cbb9;
  background: #fff;
}

.item-card--message {
  border-left: 4px solid #8c3d1f;
}

.item-card--function_call {
  border-left: 4px solid #1f6f8c;
  background: #f4fbff;
}

.item-card--function_call_output {
  border-left: 4px solid #2f855a;
  background: #f3fbf6;
}

.item-card__header,
.item-card__titleline {
  display: flex;
  gap: 0.65rem;
  align-items: center;
  flex-wrap: wrap;
}

.item-card__header {
  justify-content: space-between;
}

.item-kind,
.item-role,
.context-marker {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 700;
}

.item-kind {
  background: #f4e3d0;
  color: #7a3415;
}

.item-role {
  background: #e8eef4;
  color: #35506b;
  text-transform: capitalize;
}

.context-marker {
  background: #fff1cc;
  color: #8a5a00;
}

.item-tool-name,
.item-timestamp {
  color: #243b53;
}

.message-text,
.payload-panel pre {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.55;
}

.message-text--code,
.payload-panel pre {
  padding: 0.9rem;
  border-radius: 0.8rem;
  background: #f7f4ef;
  font-family: 'Cascadia Code', 'Courier New', monospace;
  font-size: 0.94rem;
}

.payload-panel {
  display: grid;
  gap: 0.55rem;
}

.payload-panel summary {
  cursor: pointer;
  color: #35506b;
  font-weight: 700;
}

@media (max-width: 720px) {
  .detail-header {
    flex-direction: column;
    align-items: start;
  }

  .item-card__header {
    align-items: start;
  }
}
</style>