<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { ApiError, createApiClient } from "../api";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import PanelHeading from "../components/PanelHeading.vue";
import { loadSessionDetail } from "../sessions";
import type { ConversationRecord, SessionRecord } from "../types";

const apiClient = createApiClient();
const route = useRoute();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const session = ref<SessionRecord | null>(null);
const conversations = ref<ConversationRecord[]>([]);

const sessionId = computed(() => String(route.params.sessionId ?? ""));

const sessionMetricItems = computed(() => {
  if (!session.value) return [];

  return [
    { label: "Session ID", value: session.value.id, valueClass: "kv-grid__mono" },
    { label: "AI backend", value: session.value.ai_backend },
    { label: "Total tokens", value: session.value.total_tokens.toLocaleString() },
    { label: "Input tokens", value: session.value.total_input_tokens.toLocaleString() },
    { label: "Output tokens", value: session.value.total_output_tokens.toLocaleString() },
    { label: "Prompt cost", value: `$${session.value.prompt_pricing.toFixed(4)}` },
    { label: "Completion cost", value: `$${session.value.completion_pricing.toFixed(4)}` },
    { label: "Total cost", value: `$${session.value.total_cost.toFixed(4)}` },
  ];
});

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short", hour12: false });
}

watch(
  sessionId,
  async (value) => {
    loading.value = true;
    errorMessage.value = null;

    try {
      const result = await loadSessionDetail(apiClient, value);
      session.value = result.session;
      conversations.value = result.conversations;
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.message : "Unable to load session detail.";
      session.value = null;
      conversations.value = [];
    } finally {
      loading.value = false;
    }
  },
  { immediate: true },
);
</script>

<template>
  <section class="page session-detail-page">
    <header class="page-header">
      <div class="page-header__breadcrumb">
        <RouterLink to="/sessions" class="breadcrumb-link">← Sessions</RouterLink>
        <h2 v-if="session" class="page-title">{{ formatDate(session.session_date) }}</h2>
        <h2 v-else class="page-title">Session detail</h2>
      </div>
      <span v-if="session" class="tag tag--accent">{{ session.ai_backend }}</span>
    </header>

    <p v-if="loading" class="muted-copy">Loading…</p>
    <p v-else-if="errorMessage" class="muted-copy error-copy">{{ errorMessage }}</p>

    <template v-else-if="session">
      <section class="detail-grid">
        <article class="panel">
          <PanelHeading eyebrow="Session overview" title="Metrics">
            <template #aside>
              <span class="pill pill--amber">Read only</span>
            </template>
          </PanelHeading>
          <KeyValueGrid class="list-block-spacing" :items="sessionMetricItems" />
        </article>

        <article class="panel">
          <PanelHeading
            eyebrow="Conversations"
            :title="`${conversations.length} records`"
          />

          <p v-if="conversations.length === 0" class="muted-copy list-block-spacing">
            No conversations recorded for this session.
          </p>

          <ul v-else class="list list-block-spacing">
            <li
              v-for="conversation in conversations"
              :key="conversation.id"
              class="list-row conversation-row"
            >
              <div class="conversation-row__head">
                <span class="tag" :class="conversation.status === 'closed' ? '' : 'tag--ok'">
                  {{ conversation.status }}
                </span>
                <span class="tag">{{ conversation.trigger }}</span>
              </div>
              <p class="conversation-row__time">{{ formatDate(conversation.created_at) }}</p>
              <div class="conversation-row__stats">
                <span class="tag">{{ conversation.item_count }} items</span>
              </div>
            </li>
          </ul>
        </article>
      </section>
    </template>
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

.page-header__breadcrumb {
  display: grid;
  gap: 4px;
}

.breadcrumb-link {
  color: var(--accent);
  font-size: 0.78rem;
  font-family: var(--display);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  transition: color 150ms ease;
}

.breadcrumb-link:hover {
  color: var(--accent-strong);
}

.page-title {
  margin: 0;
  font-family: var(--display);
  font-size: clamp(1.5rem, 2.5vw, 2.2rem);
  line-height: 0.95;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.conversation-row {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
}

.conversation-row__head {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.conversation-row__time {
  margin: 0;
  font-size: 0.82rem;
  color: var(--text-dim);
}

.conversation-row__stats {
  display: flex;
  gap: 6px;
}
</style>
