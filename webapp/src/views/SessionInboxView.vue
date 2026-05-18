<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { createApiClient, ApiError } from "../api";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PageHeader from "../components/PageHeader.vue";
import StatGrid from "../components/StatGrid.vue";
import { formatDate, formatUsd } from "../formatters";
import { loadSessionInbox } from "../sessions";
import type { PaginatedResponse, SessionRecord } from "../types";

const apiClient = createApiClient();

const inbox = ref<PaginatedResponse<SessionRecord> | null>(null);
const loading = ref(true);
const errorMessage = ref<string | null>(null);

function sessionStatItems(session: SessionRecord) {
  return [
    { label: "Conversations", value: session.conversations.length },
    { label: "Tokens", value: session.total_tokens.toLocaleString() },
    { label: "Cost", value: formatUsd(session.total_cost), valueClass: "stat-tile__value--cost" },
  ];
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
    <PageHeader eyebrow="Coaching sessions" title="Sessions">
      <template #actions>
        <span class="pill pill--amber">Read only</span>
      </template>
    </PageHeader>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Recent sessions</p>
          <h3>{{ inbox ? `${inbox.docs_quantity} sessions` : "Sessions" }}</h3>
        </div>
        <span v-if="inbox" class="pill">Recent first</span>
      </div>

      <LoadingErrorEmpty
        :loading="loading"
        :error="errorMessage"
        :empty="!inbox || inbox.docs.length === 0"
        loading-message="Loading…"
        empty-message="No sessions recorded yet."
        loading-class="muted-copy list-block-spacing"
        error-class="muted-copy list-block-spacing error-copy"
        empty-class="muted-copy list-block-spacing"
      >
        <ul class="list list-block-spacing">
          <li
            v-for="session in inbox?.docs ?? []"
            :key="session.id"
            class="list-row list-row--linked session-row"
          >
            <RouterLink :to="`/sessions/${session.id}`" class="list-row__overlay" aria-label="Open session" />

            <div class="session-row__main">
              <div class="session-row__head">
                <strong class="session-row__date">{{ formatDate(session.session_date) }}</strong>
                <span class="tag tag--accent">{{ session.ai_backend }}</span>
              </div>
            </div>

            <StatGrid :items="sessionStatItems(session)" inline />
          </li>
        </ul>
      </LoadingErrorEmpty>
    </section>
  </section>
</template>

<style scoped>
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

@media (max-width: 700px) {
  .session-row {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}
</style>
