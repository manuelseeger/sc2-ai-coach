<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError, createApiClient } from "../api";
import {
  getConversationInboxState,
  loadConversationInbox,
  setConversationInboxState,
} from "../conversations";
import type { ConversationRecord, PaginatedResponse } from "../types";

const apiClient = createApiClient();
const restoredState = getConversationInboxState();

const inbox = ref<PaginatedResponse<ConversationRecord> | null>(null);
const loading = ref(true);
const errorMessage = ref<string | null>(null);
const selectedConversationId = ref<string | null>(restoredState.selectedConversationId);
const filters = reactive({
  trigger: String(restoredState.params.trigger ?? "all"),
  status: String(restoredState.params.status ?? "all"),
  currentPage: Number(restoredState.params.current_page ?? 1),
  docsPerPage: Number(restoredState.params.docs_per_page ?? 25),
});

const triggerOptions = [
  { value: "all", label: "All triggers" },
  { value: "wake", label: "Wake word" },
  { value: "repl", label: "REPL" },
  { value: "game_start", label: "Game start" },
  { value: "new_replay", label: "New replay" },
  { value: "twitch_chat", label: "Twitch chat" },
  { value: "twitch_follow", label: "Twitch follow" },
  { value: "twitch_raid", label: "Twitch raid" },
  { value: "cast_replay", label: "Cast replay" },
  { value: "replay_summary", label: "Replay summary" },
];

const statusOptions = [
  { value: "all", label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "closed", label: "Closed" },
  { value: "failed", label: "Failed" },
];

function formatDate(value: string | null): string {
  if (!value) {
    return "No activity yet";
  }
  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
    hour12: false,
  });
}

function saveState(): void {
  setConversationInboxState({
    params: {
      sort: "-created_at",
      current_page: filters.currentPage,
      docs_per_page: filters.docsPerPage,
      trigger: filters.trigger === "all" ? undefined : filters.trigger,
      status: filters.status === "all" ? undefined : filters.status,
    },
    selectedConversationId: selectedConversationId.value,
  });
}

async function refreshInbox(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;

  try {
    inbox.value = await loadConversationInbox(apiClient, {
      sort: "-created_at",
      current_page: filters.currentPage,
      docs_per_page: filters.docsPerPage,
      trigger: filters.trigger === "all" ? undefined : filters.trigger,
      status: filters.status === "all" ? undefined : filters.status,
    });
    saveState();
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : "Unable to load conversations.";
  } finally {
    loading.value = false;
  }
}

function openConversation(conversationId: string): void {
  selectedConversationId.value = conversationId;
  saveState();
}

const emptyState = computed(() => {
  if (filters.trigger === "all" && filters.status === "all") {
    return "No persisted conversations recorded yet.";
  }

  const triggerLabel = triggerOptions.find((option) => option.value === filters.trigger)?.label;
  const statusLabel = statusOptions.find((option) => option.value === filters.status)?.label;
  const parts = [triggerLabel, statusLabel].filter((value) => value && value !== "All triggers" && value !== "All statuses");
  return `No conversations matched ${parts.join(" and ")}.`;
});

onMounted(async () => {
  await refreshInbox();
});
</script>

<template>
  <section class="page conversation-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Conversation review</p>
        <h2 class="page-title">Conversations</h2>
      </div>
      <RouterLink to="/resources/conversations" class="button button--ghost">
        Maintenance
      </RouterLink>
    </header>

    <section class="panel filter-panel">
      <div class="filter-row">
        <label class="filter-field">
          <span class="form-label">Trigger</span>
          <select v-model="filters.trigger" class="select-input">
            <option v-for="option in triggerOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>

        <label class="filter-field">
          <span class="form-label">Status</span>
          <select v-model="filters.status" class="select-input">
            <option v-for="option in statusOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>

        <label class="filter-field filter-field--narrow">
          <span class="form-label">Page</span>
          <input v-model.number="filters.currentPage" class="text-input" type="number" min="1" />
        </label>

        <div class="filter-field filter-field--action">
          <span class="form-label">&nbsp;</span>
          <button type="button" class="button button--accent" @click="refreshInbox">Apply</button>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Transcript inbox</p>
          <h3>{{ inbox ? `${inbox.docs_quantity} conversations` : "Conversations" }}</h3>
        </div>
        <span class="pill pill--amber">Read oriented</span>
      </div>

      <p v-if="loading" class="muted-copy list-block-spacing">Loading…</p>
      <p v-else-if="errorMessage" class="muted-copy list-block-spacing error-copy">{{ errorMessage }}</p>
      <p v-else-if="!inbox || inbox.docs.length === 0" class="muted-copy list-block-spacing">
        {{ emptyState }}
      </p>

      <ul v-else class="list list-block-spacing">
        <li
          v-for="conversation in inbox.docs"
          :key="conversation.id"
          class="list-row list-row--linked conversation-row"
          :class="{ 'conversation-row--selected': selectedConversationId === conversation.id }"
        >
          <RouterLink
            :to="`/conversations/${conversation.id}`"
            class="list-row__overlay"
            aria-label="Open conversation"
            @click="openConversation(conversation.id)"
          />

          <div class="conversation-row__main">
            <div class="conversation-row__head">
              <span class="tag" :class="conversation.status === 'active' ? 'tag--ok' : ''">
                {{ conversation.status }}
              </span>
              <span class="tag">{{ triggerOptions.find((option) => option.value === conversation.trigger)?.label ?? conversation.trigger }}</span>
            </div>
            <strong class="conversation-row__title">{{ conversation.title || "Untitled conversation" }}</strong>
            <p class="conversation-row__meta">
              Started {{ formatDate(conversation.created_at) }}
              <span v-if="conversation.last_item_at"> · Last item {{ formatDate(conversation.last_item_at) }}</span>
            </p>
          </div>

          <div class="conversation-row__stats">
            <span class="tag">{{ conversation.item_count }} items</span>
            <span v-if="conversation.session" class="tag mono-copy">Session linked</span>
            <span v-if="conversation.replay_id" class="tag mono-copy">Replay linked</span>
          </div>
        </li>
      </ul>

      <div v-if="inbox && inbox.page_quantity > 1" class="pagination-row">
        <button
          class="button button--ghost"
          :disabled="filters.currentPage <= 1"
          @click="filters.currentPage--; refreshInbox()"
        >
          ← Prev
        </button>
        <span class="pagination-label">{{ filters.currentPage }} / {{ inbox.page_quantity }}</span>
        <button
          class="button button--ghost"
          :disabled="filters.currentPage >= inbox.page_quantity"
          @click="filters.currentPage++; refreshInbox()"
        >
          Next →
        </button>
      </div>
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

.filter-panel {
  display: grid;
  gap: 14px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 14px;
}

.filter-field {
  display: grid;
  gap: 6px;
  flex: 1 1 180px;
}

.filter-field--narrow {
  flex: 0 1 120px;
}

.filter-field--action {
  flex: 0 0 auto;
}

.conversation-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 20px;
  padding: 16px 20px;
}

.conversation-row--selected {
  border-color: var(--accent-border);
  box-shadow: inset 0 0 0 1px rgba(86, 194, 255, 0.16);
}

.conversation-row__main {
  display: grid;
  gap: 6px;
}

.conversation-row__head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.conversation-row__title {
  font-family: var(--display);
  font-size: 1rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.conversation-row__meta {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.88rem;
}

.conversation-row__stats {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-content: start;
  gap: 8px;
}

.pagination-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-muted);
}

.pagination-label {
  color: var(--text-muted);
  font-family: var(--display);
  font-size: 0.8rem;
  letter-spacing: 0.08em;
}

@media (max-width: 700px) {
  .conversation-row {
    grid-template-columns: 1fr;
  }

  .conversation-row__stats {
    justify-content: flex-start;
  }
}
</style>