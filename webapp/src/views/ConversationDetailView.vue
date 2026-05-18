<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { ApiError, createApiClient } from "../api";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import PanelHeading from "../components/PanelHeading.vue";
import { loadConversationDetail } from "../conversations";
import type { ConversationItemRecord, ConversationRecord, ResponseRecord } from "../types";

const apiClient = createApiClient();
const route = useRoute();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const notFound = ref(false);
const conversation = ref<ConversationRecord | null>(null);
const items = ref<ConversationItemRecord[]>([]);
const responses = ref<ResponseRecord[]>([]);

const tokenStats = computed(() => {
  if (responses.value.length === 0) return null;
  const input = responses.value.reduce((s, r) => s + r.input_tokens, 0);
  const cached = responses.value.reduce((s, r) => s + r.cached_tokens, 0);
  const output = responses.value.reduce((s, r) => s + r.output_tokens, 0);
  const cost = responses.value.reduce((s, r) => s + r.total_cost, 0);
  return [
    { label: "Input tokens", value: input.toLocaleString(), valueClass: "kv-value--token-input" },
    { label: "Cached tokens", value: cached.toLocaleString(), valueClass: "kv-value--token-cached" },
    { label: "Output tokens", value: output.toLocaleString(), valueClass: "kv-value--token-output" },
    { label: "Total cost", value: `$${cost.toFixed(4)}`, valueClass: "kv-value--cost" },
  ];
});

const conversationId = computed(() => String(route.params.conversationId ?? ""));

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "None";
  }
  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
    hour12: false,
  });
}

function triggerLabel(value: string): string {
  return {
    wake: "Wake word",
    repl: "REPL",
    game_start: "Game start",
    new_replay: "New replay",
    twitch_chat: "Twitch chat",
    twitch_follow: "Twitch follow",
    twitch_raid: "Twitch raid",
    cast_replay: "Cast replay",
    replay_summary: "Replay summary",
  }[value] ?? value;
}

function renderMessage(item: ConversationItemRecord): string {
  return item.content.map((part) => part.text).filter(Boolean).join("\n\n");
}

function isCodeLike(text: string): boolean {
  return /(\{.*\}|\[.*\]|=>|class\s+|def\s+|function\s+)/s.test(text) || /\n\s{2,}\S/.test(text);
}

function itemKindLabel(item: ConversationItemRecord): string {
  if (item.type === "function_call") {
    return "Tool call";
  }
  if (item.type === "function_call_output") {
    return "Tool result";
  }
  return item.role ? `${item.role} message` : item.type;
}

function rawArguments(item: ConversationItemRecord): string {
  return JSON.stringify(item.arguments ?? {}, null, 2);
}

async function refreshConversation(id: string): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  notFound.value = false;

  try {
    const loaded = await loadConversationDetail(apiClient, id);
    conversation.value = loaded.conversation;
    items.value = loaded.items;
    responses.value = loaded.responses;
  } catch (error) {
    if (error instanceof ApiError && error.code === "not_found") {
      notFound.value = true;
    } else {
      errorMessage.value = error instanceof ApiError ? error.message : "Unable to load conversation.";
    }
    conversation.value = null;
    items.value = [];
  } finally {
    loading.value = false;
  }
}

watch(conversationId, async (value) => {
  await refreshConversation(value);
}, { immediate: true });
</script>

<template>
  <section class="page conversation-detail-page">
    <header class="page-header">
      <div class="page-header__breadcrumb">
        <RouterLink to="/conversations" class="breadcrumb-link">← Back to conversations</RouterLink>
        <p class="eyebrow">Conversation</p>
        <h2 class="page-title">{{ conversation ? triggerLabel(conversation.trigger) : "Conversation" }}</h2>
      </div>
      <RouterLink v-if="conversation" :to="`/resources/conversations/${conversation.id}`" class="button button--ghost">
        Maintenance
      </RouterLink>
    </header>

    <p v-if="loading" class="muted-copy">Loading conversation…</p>
    <p v-else-if="notFound" class="feedback error-copy">Conversation not found. The deep link no longer resolves.</p>
    <p v-else-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>

    <template v-else-if="conversation">
      <section class="detail-grid">
        <article class="panel panel-stack">
          <PanelHeading :title="triggerLabel(conversation.trigger)">
            <template #aside>
              <span class="pill" :class="conversation.status === 'active' ? 'pill--accent' : 'pill--amber'">
                {{ conversation.status }}
              </span>
            </template>
          </PanelHeading>

          <div class="header-tags">
            <span class="tag">Created {{ formatDate(conversation.created_at) }}</span>
            <span class="tag">{{ conversation.item_count }} items</span>
            <RouterLink v-if="conversation.session" :to="`/sessions/${conversation.session}`" class="tag tag--link tag--accent">
              Session →
            </RouterLink>
            <RouterLink v-if="conversation.replay_id" :to="`/replays/${conversation.replay_id}`" class="tag tag--link tag--ok">
              Replay →
            </RouterLink>
          </div>

          <p v-if="conversation.handler_context" class="panel-intro">
            {{ conversation.handler_context }}
          </p>

          <template v-if="tokenStats">
            <p class="eyebrow token-eyebrow">Token usage</p>
            <div class="token-grid">
              <KeyValueGrid :items="tokenStats" />
            </div>
          </template>
        </article>

        <article class="panel panel-stack">
          <PanelHeading eyebrow="Transcript" :title="`${items.length} persisted items`" />

          <p v-if="items.length === 0" class="muted-copy">No conversation items were persisted for this exchange.</p>

          <ol v-else class="transcript-list">
            <li v-for="item in items" :key="item.id" class="transcript-item" :class="[`transcript-item--${item.type}`, item.role ? `role--${item.role}` : '']">
              <div class="transcript-item__meta">
                <span class="tag">{{ itemKindLabel(item) }}</span>
                <span v-if="item.name" class="tag tag--accent">{{ item.name }}</span>
                <span v-if="!item.included_in_context" class="tag tag--warn">Excluded from model context</span>
                <time class="transcript-item__time">{{ formatDate(item.created_at) }}</time>
              </div>

              <pre
                v-if="item.type === 'message'"
                class="transcript-item__body"
                :class="{ 'transcript-item__body--code': isCodeLike(renderMessage(item)) }"
              >{{ renderMessage(item) }}</pre>

              <details v-else-if="item.type === 'function_call'" class="transcript-item__details">
                <summary>Raw arguments</summary>
                <pre class="transcript-item__body transcript-item__body--code">{{ rawArguments(item) }}</pre>
              </details>

              <details v-else-if="item.type === 'function_call_output'" class="transcript-item__details">
                <summary>Raw result</summary>
                <pre class="transcript-item__body transcript-item__body--code">{{ item.output || "" }}</pre>
              </details>
            </li>
          </ol>
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
}

.page-title {
  margin: 4px 0 0;
  font-family: var(--display);
  font-size: clamp(1.8rem, 3vw, 2.6rem);
  line-height: 0.93;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(0, 2fr);
  gap: 16px;
  align-items: start;
}

.header-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag--link {
  text-decoration: none;
}

.transcript-list {
  display: grid;
  gap: 12px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.transcript-item {
  display: grid;
  gap: 10px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: linear-gradient(180deg, rgba(14, 21, 33, 0.94), rgba(9, 14, 22, 0.98));
}

.transcript-item--message.role--user {
  border-left: 3px solid rgba(251, 191, 36, 0.5);
}

.transcript-item--message.role--assistant {
  border-left: 3px solid rgba(86, 194, 255, 0.5);
}

.transcript-item--function_call {
  border-left: 3px solid rgba(251, 191, 36, 0.4);
}

.transcript-item--function_call_output {
  border-left: 3px solid rgba(74, 222, 128, 0.4);
}

.transcript-item__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.transcript-item__time {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 0.78rem;
}

.transcript-item__body {
  margin: 0;
  white-space: pre-wrap;
  color: var(--text);
  font-family: var(--ui);
  line-height: 1.6;
}

.transcript-item__body--code {
  padding: 14px;
  border-radius: var(--radius-sm);
  background: rgba(7, 10, 16, 0.9);
  border: 1px solid var(--border-muted);
  font-family: var(--mono);
  font-size: 0.82rem;
}

.transcript-item__details summary {
  cursor: pointer;
  color: var(--accent-strong);
  font-family: var(--display);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.token-eyebrow {
  margin-bottom: -4px;
}

.token-grid :deep(.data-grid) {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}


@media (max-width: 700px) {
  .page-header {
    align-items: start;
    flex-direction: column;
  }

  .transcript-item__time {
    margin-left: 0;
  }
}
</style>