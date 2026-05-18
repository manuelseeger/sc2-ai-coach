<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError, createApiClient } from "../api";
import FormField from "../components/FormField.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PageHeader from "../components/PageHeader.vue";
import PaginationControls from "../components/PaginationControls.vue";
import {
  getConversationInboxState,
  loadConversationInbox,
  setConversationInboxState,
} from "../conversations";
import { formatDate, triggerClass, triggerLabel } from "../formatters";
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
    <PageHeader eyebrow="Conversation review" title="Conversations">
      <template #actions>
        <RouterLink to="/resources/conversations" class="button button--ghost">
          Maintenance
        </RouterLink>
      </template>
    </PageHeader>

    <section class="panel inbox-pane inbox-pane--filter">
      <div class="inbox-filter-row">
        <FormField label="Trigger" class="inbox-filter-field">
          <select v-model="filters.trigger" class="select-input">
            <option v-for="option in triggerOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </FormField>

        <FormField label="Status" class="inbox-filter-field">
          <select v-model="filters.status" class="select-input">
            <option v-for="option in statusOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </FormField>

        <FormField label="Page" class="inbox-filter-field inbox-filter-field--narrow">
          <input v-model.number="filters.currentPage" class="text-input" type="number" min="1" @keyup.enter="refreshInbox" />
        </FormField>

        <div class="inbox-filter-field inbox-filter-field--action">
          <span class="form-label">&nbsp;</span>
          <button type="button" class="button button--accent" @click="refreshInbox">Apply</button>
        </div>
      </div>
    </section>

    <section class="panel inbox-pane">
      <PanelHeading eyebrow="Results" :title="inbox ? `${inbox.docs_quantity} conversations` : 'Conversations'">
        <template #aside>
          <span v-if="inbox" class="pill">
            Page {{ inbox.current_page }} of {{ inbox.page_quantity }}
          </span>
        </template>
      </PanelHeading>

      <LoadingErrorEmpty
        :loading="loading"
        :error="errorMessage"
        :empty="!inbox || inbox.docs.length === 0"
        loading-message="Loading…"
        :empty-message="emptyState"
        loading-class="muted-copy list-block-spacing"
        error-class="muted-copy list-block-spacing error-copy"
        empty-class="muted-copy list-block-spacing"
      >
        <ul class="list list-block-spacing">
          <li
            v-for="conversation in inbox?.docs ?? []"
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
                <span class="tag" :class="triggerClass(conversation.trigger)">{{ triggerLabel(conversation.trigger) }}</span>
              </div>
              <p class="conversation-row__meta">
                Started {{ formatDate(conversation.created_at, 'No activity yet') }}
                <span v-if="conversation.last_item_at"> · Last item {{ formatDate(conversation.last_item_at, 'No activity yet') }}</span>
              </p>
            </div>

            <div class="conversation-row__stats">
              <span class="tag">{{ conversation.item_count }} items</span>
              <span v-if="conversation.session" class="tag">Session linked</span>
              <span v-if="conversation.replay_id" class="tag">Replay linked</span>
            </div>
          </li>
        </ul>

        <PaginationControls
          :current-page="filters.currentPage"
          :total-pages="inbox?.page_quantity ?? 1"
          @prev="filters.currentPage--; refreshInbox()"
          @next="filters.currentPage++; refreshInbox()"
        />
      </LoadingErrorEmpty>
    </section>
  </section>
</template>

<style scoped>
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

@media (max-width: 700px) {
  .conversation-row {
    grid-template-columns: 1fr;
  }

  .conversation-row__stats {
    justify-content: flex-start;
  }
}
</style>