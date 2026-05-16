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
  if (!session.value) {
    return [];
  }

  return [
    { label: "Session ID", value: session.value.id },
    { label: "Current conversation", value: session.value.current_conversation ?? "None" },
    { label: "Twitch conversation", value: session.value.twitch_conversation ?? "None" },
    { label: "Total tokens", value: session.value.total_tokens },
    { label: "Total input tokens", value: session.value.total_input_tokens },
    { label: "Total output tokens", value: session.value.total_output_tokens },
    { label: "Prompt pricing", value: `$${session.value.prompt_pricing.toFixed(2)}` },
    { label: "Completion pricing", value: `$${session.value.completion_pricing.toFixed(2)}` },
    { label: "Total cost", value: `$${session.value.total_cost.toFixed(2)}` },
  ];
});

function formatDate(value: string | null): string {
  if (!value) {
    return "Not recorded";
  }

  return new Date(value).toLocaleString();
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
    <header class="panel detail-hero">
      <div>
        <p class="eyebrow">Session detail</p>
        <h2>Persisted session review</h2>
        <p class="panel-intro">
          Read-only session data with linked conversations loaded from the backend relationship
          route.
        </p>
      </div>

      <RouterLink to="/sessions" class="pill pill--accent">Back to inbox</RouterLink>
    </header>

    <p v-if="loading" class="muted-copy">Loading session detail...</p>
    <p v-else-if="errorMessage" class="muted-copy">{{ errorMessage }}</p>

    <template v-else-if="session">
      <section class="detail-grid">
        <article class="panel">
          <PanelHeading eyebrow="Overview" :title="formatDate(session.session_date)">
            <template #aside>
              <span class="tag">{{ session.ai_backend }}</span>
            </template>
          </PanelHeading>

          <KeyValueGrid class="session-metrics" :items="sessionMetricItems" />
        </article>

        <article class="panel">
          <PanelHeading
            eyebrow="Linked conversations"
            :title="`${conversations.length} persisted records`"
          >
            <template #aside>
              <span class="pill pill--amber">Read only</span>
            </template>
          </PanelHeading>

          <ul v-if="conversations.length > 0" class="list conversation-list">
            <li v-for="conversation in conversations" :key="conversation.id" class="list-row">
              <div class="conversation-topline">
                <strong>{{ conversation.title || conversation.id }}</strong>
                <span class="tag">{{ conversation.status }}</span>
              </div>
              <p>
                Trigger {{ conversation.trigger }}. Created
                {{ formatDate(conversation.created_at) }}.
              </p>
              <div class="tag-row">
                <span class="tag">{{ conversation.item_count }} items</span>
                <span class="tag">Last item {{ formatDate(conversation.last_item_at) }}</span>
              </div>
            </li>
          </ul>

          <p v-else class="muted-copy">No linked conversations were recorded for this session.</p>
        </article>
      </section>
    </template>
  </section>
</template>

<style scoped>
.detail-hero {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
}

.detail-hero h2 {
  margin: 8px 0 12px;
  font-family: var(--font-display);
  font-size: clamp(2rem, 3vw, 3.2rem);
  line-height: 0.94;
  text-transform: uppercase;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 20px;
}

.session-metrics {
  margin-top: 18px;
}

.conversation-list {
  margin-top: 18px;
}

.conversation-topline {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
}

@media (max-width: 900px) {
  .detail-hero,
  .conversation-topline {
    flex-direction: column;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>