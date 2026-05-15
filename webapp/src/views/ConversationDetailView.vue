<template>
  <section class="detail-shell">
    <p class="eyebrow">Conversation Review</p>
    <header v-if="summary" class="detail-header">
      <div>
        <h1>Conversation review</h1>
        <p class="detail-copy">
          Dedicated conversation route for transcript review and future item flow rendering.
        </p>
      </div>
      <RouterLink class="back-link" to="/conversations">Back to inbox</RouterLink>
    </header>

    <p v-if="loading" class="detail-copy">Loading conversation…</p>
    <p v-else-if="error" class="detail-error">{{ error }}</p>

    <article v-else-if="summary" class="summary-card">
      <h2>{{ summary.id }}</h2>
      <dl class="summary-facts">
        <div>
          <dt>Trigger</dt>
          <dd>{{ formatTrigger(summary.trigger) }}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{{ formatStatus(summary.status) }}</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{{ formatUtcDate(summary.created_at) }}</dd>
        </div>
        <div>
          <dt>Items</dt>
          <dd>{{ summary.item_count }} items</dd>
        </div>
        <div>
          <dt>Replay</dt>
          <dd>{{ summary.replay_id ?? 'None' }}</dd>
        </div>
        <div>
          <dt>Session</dt>
          <dd>{{ summary.session_id ?? 'None' }}</dd>
        </div>
      </dl>
    </article>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { useAdminApi } from '../api'
import { formatStatus, formatTrigger, formatUtcDate } from '../format'
import type { ConversationSummary } from '../types'

const client = useAdminApi()
const route = useRoute()

const loading = ref(true)
const error = ref('')
const summary = ref<ConversationSummary | null>(null)

onMounted(async () => {
  try {
    summary.value = await client.getConversationSummary(String(route.params.conversationId))
  } catch (loadError) {
    error.value = loadError instanceof Error ? loadError.message : 'Unable to load conversation.'
  } finally {
    loading.value = false
  }
})
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

.back-link {
  color: #8c3d1f;
  font-weight: 700;
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

@media (max-width: 720px) {
  .detail-header {
    flex-direction: column;
    align-items: start;
  }
}
</style>