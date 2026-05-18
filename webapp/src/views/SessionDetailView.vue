<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { ApiError, createApiClient } from "../api";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PanelHeading from "../components/PanelHeading.vue";
import PageHeader from "../components/PageHeader.vue";
import { formatDate, triggerClass, triggerLabel } from "../formatters";
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
    { label: "AI backend", value: session.value.ai_backend },
    { label: "Total tokens", value: session.value.total_tokens.toLocaleString() },
    { label: "Input tokens", value: session.value.total_input_tokens.toLocaleString(), valueClass: "kv-value--token-input" },
    { label: "Cached tokens", value: session.value.total_cached_tokens.toLocaleString(), valueClass: "kv-value--token-cached" },
    { label: "Output tokens", value: session.value.total_output_tokens.toLocaleString(), valueClass: "kv-value--token-output" },
    { label: "Prompt cost", value: `$${session.value.prompt_pricing.toFixed(4)}`, valueClass: "kv-value--cost" },
    { label: "Completion cost", value: `$${session.value.completion_pricing.toFixed(4)}`, valueClass: "kv-value--cost" },
    { label: "Total cost", value: `$${session.value.total_cost.toFixed(4)}`, valueClass: "kv-value--cost" },
  ];
});

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
    <PageHeader
      :title="session ? formatDate(session.session_date) : 'Session detail'"
      breadcrumb-label="← Sessions"
      breadcrumb-to="/sessions"
    >
      <template #actions>
        <span v-if="session" class="tag tag--accent">{{ session.ai_backend }}</span>
      </template>
    </PageHeader>

    <LoadingErrorEmpty :loading="loading" :error="errorMessage" loading-message="Loading…" error-class="muted-copy error-copy">
      <template v-if="session">
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
              class="list-row list-row--linked conversation-row"
            >
              <RouterLink
                :to="`/conversations/${conversation.id}`"
                class="list-row__overlay"
                aria-label="Open conversation"
              />
              <div class="conversation-row__head">
                <span class="tag" :class="conversation.status === 'closed' ? '' : 'tag--ok'">
                  {{ conversation.status }}
                </span>
                <span class="tag" :class="triggerClass(conversation.trigger)">{{ triggerLabel(conversation.trigger) }}</span>
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
    </LoadingErrorEmpty>
  </section>
</template>

<style scoped>
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
