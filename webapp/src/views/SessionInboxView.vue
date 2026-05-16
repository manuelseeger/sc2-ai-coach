<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { createApiClient, ApiError } from "../api";
import { loadSessionInbox } from "../sessions";
import type { PaginatedResponse, SessionRecord } from "../types";

const apiClient = createApiClient();

const inbox = ref<PaginatedResponse<SessionRecord> | null>(null);
const loading = ref(true);
const errorMessage = ref<string | null>(null);

function formatDate(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatCost(value: number): string {
  return `$${value.toFixed(4)}`;
}

onMounted(async () => {
  try {
    inbox.value = await loadSessionInbox(apiClient);
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : "Unable to load sessions.";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="page sessions-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Coaching sessions</p>
        <h2 class="page-title">Sessions</h2>
      </div>
      <span class="pill pill--amber">Read only</span>
    </header>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Recent sessions</p>
          <h3>{{ inbox ? `${inbox.docs_quantity} sessions` : "Sessions" }}</h3>
        </div>
        <span v-if="inbox" class="pill">Recent first</span>
      </div>

      <p v-if="loading" class="muted-copy list-block-spacing">Loading…</p>
      <p v-else-if="errorMessage" class="muted-copy list-block-spacing error-copy">{{ errorMessage }}</p>
      <p v-else-if="!inbox || inbox.docs.length === 0" class="muted-copy list-block-spacing">
        No sessions recorded yet.
      </p>

      <ul v-else class="list list-block-spacing">
        <li
          v-for="session in inbox.docs"
          :key="session.id"
          class="list-row list-row--linked session-row"
        >
          <RouterLink :to="`/sessions/${session.id}`" class="list-row__overlay" aria-label="Open session" />

          <div class="session-row__main">
            <div class="session-row__head">
              <strong class="session-row__date">{{ formatDate(session.session_date) }}</strong>
              <span class="tag">{{ session.ai_backend }}</span>
            </div>
            <p class="session-row__id mono-copy">{{ session.id }}</p>
          </div>

          <div class="session-row__stats">
            <div class="stat-item">
              <span class="stat-item__label">Conversations</span>
              <span class="stat-item__value">{{ session.conversations.length }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-item__label">Tokens</span>
              <span class="stat-item__value">{{ session.total_tokens.toLocaleString() }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-item__label">Cost</span>
              <span class="stat-item__value">{{ formatCost(session.total_cost) }}</span>
            </div>
          </div>
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 8px;
}

.page-title {
  margin: 4px 0 0;
  font-family: var(--display);
  font-size: clamp(1.8rem, 3vw, 2.6rem);
  line-height: 0.93;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.session-row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 24px;
  padding: 16px 20px;
}

.session-row__main {
  display: grid;
  gap: 6px;
}

.session-row__head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.session-row__date {
  font-size: 1rem;
  font-family: var(--display);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.session-row__id {
  font-size: 0.78rem;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 40ch;
}

.session-row__stats {
  display: flex;
  gap: 32px;
}

.stat-item {
  display: grid;
  gap: 4px;
  text-align: right;
}

.stat-item__label {
  color: var(--text-muted);
  font-size: 0.68rem;
  font-family: var(--display);
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.stat-item__value {
  color: var(--text);
  font-family: var(--display);
  font-size: 0.95rem;
  letter-spacing: 0.04em;
}

@media (max-width: 700px) {
  .session-row {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .session-row__stats {
    gap: 20px;
  }

  .stat-item {
    text-align: left;
  }
}
</style>
