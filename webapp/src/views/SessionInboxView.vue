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
  return new Date(value).toLocaleString();
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
    <header class="panel sessions-hero">
      <div>
        <p class="eyebrow">Session review</p>
        <h2>Recent coaching sessions</h2>
        <p class="panel-intro">
          Read-only session inbox backed directly by the standalone admin API. Open a row to
          inspect persisted fields and linked conversations.
        </p>
      </div>

      <div class="tag-row">
        <span class="pill pill--accent">Recent-first</span>
        <span class="pill pill--amber">Read only</span>
      </div>
    </header>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Inbox</p>
          <h3>Persisted sessions</h3>
        </div>
        <span v-if="inbox" class="pill">{{ inbox.docs_quantity }} sessions</span>
      </div>

      <p v-if="loading" class="muted-copy">Loading session inbox...</p>
      <p v-else-if="errorMessage" class="muted-copy">{{ errorMessage }}</p>
      <p v-else-if="!inbox || inbox.docs.length === 0" class="muted-copy">
        No sessions available.
      </p>

      <ul v-else class="list session-list">
        <li v-for="session in inbox.docs" :key="session.id" class="list-row session-row">
          <div class="session-row__topline">
            <div>
              <strong>{{ formatDate(session.session_date) }}</strong>
              <p>Session ID: {{ session.id }}</p>
            </div>
            <span class="tag">{{ session.ai_backend }}</span>
          </div>

          <div class="tag-row">
            <span class="tag">{{ session.conversations.length }} conversations</span>
            <span class="tag">{{ session.total_tokens }} total tokens</span>
            <span class="tag">${{ session.total_cost.toFixed(2) }} total cost</span>
          </div>

          <RouterLink :to="`/sessions/${session.id}`" class="session-row__link">
            Open session detail
          </RouterLink>
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.sessions-hero {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
}

.sessions-hero h2 {
  margin: 8px 0 12px;
  font-family: var(--font-display);
  font-size: clamp(2rem, 3vw, 3.2rem);
  line-height: 0.94;
  text-transform: uppercase;
}

.session-list {
  margin-top: 18px;
}

.session-row {
  gap: 14px;
}

.session-row__topline {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
}

.session-row__link {
  color: var(--accent-strong);
  font-family: var(--font-display);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

@media (max-width: 720px) {
  .sessions-hero,
  .session-row__topline {
    flex-direction: column;
  }
}
</style>