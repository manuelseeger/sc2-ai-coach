<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError, createApiClient } from "../api";
import PanelHeading from "../components/PanelHeading.vue";
import { loadConversationInbox, queryConversationRecords } from "../conversations";
import type { ConversationRecord, PaginatedResponse, QueryBody } from "../types";

const apiClient = createApiClient();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const result = ref<PaginatedResponse<ConversationRecord> | null>(null);
const resultMode = ref<"list" | "query">("list");

const filters = reactive({
  session: "",
  trigger: "",
  status: "",
  sort: "-created_at",
  currentPage: 1,
  docsPerPage: 25,
});

const queryText = ref(`{
  "filter": {
    "metadata.scope": "conversation-crud"
  },
  "sort": {
    "created_at": -1
  },
  "current_page": 1,
  "docs_per_page": 10
}`);

function formatDate(value: string): string {
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short", hour12: false });
}

async function refreshList(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  resultMode.value = "list";

  try {
    result.value = await loadConversationInbox(apiClient, {
      session: filters.session || undefined,
      trigger: filters.trigger || undefined,
      status: filters.status || undefined,
      sort: filters.sort || undefined,
      current_page: filters.currentPage,
      docs_per_page: filters.docsPerPage,
    });
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Unable to load conversations.";
  } finally {
    loading.value = false;
  }
}

async function runAdvancedQuery(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  resultMode.value = "query";

  try {
    result.value = await queryConversationRecords(apiClient, JSON.parse(queryText.value) as QueryBody);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Advanced conversation query failed.";
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await refreshList();
});
</script>

<template>
  <section class="page conversation-resource-page">
    <header class="panel page-hero">
      <div>
        <p class="eyebrow">Conversation management</p>
        <h2 class="page-hero__title">Browse and manage conversations</h2>
        <p class="panel-intro">
          Search and manage conversation records. Messages are managed separately within each conversation.
        </p>
      </div>

      <div class="button-row">
        <span class="pill pill--accent">Editable</span>
        <RouterLink to="/resources/conversations/new" class="button button--accent">
          Create conversation
        </RouterLink>
      </div>
    </header>

    <section class="results-grid">
      <article class="panel panel-stack">
        <PanelHeading eyebrow="Filters" title="Browse conversations" />

        <div class="form-grid">
          <label class="form-field">
            <span class="form-label">Session</span>
            <input v-model="filters.session" class="text-input mono-copy" type="text" />
          </label>

          <label class="form-field">
            <span class="form-label">Trigger</span>
            <input v-model="filters.trigger" class="text-input" type="text" />
          </label>

          <label class="form-field">
            <span class="form-label">Status</span>
            <input v-model="filters.status" class="text-input" type="text" />
          </label>

          <label class="form-field">
            <span class="form-label">Sort</span>
            <input v-model="filters.sort" class="text-input mono-copy" type="text" />
          </label>

          <label class="form-field">
            <span class="form-label">Page</span>
            <input v-model.number="filters.currentPage" class="text-input" type="number" min="1" />
          </label>

          <label class="form-field">
            <span class="form-label">Per page</span>
            <input v-model.number="filters.docsPerPage" class="text-input" type="number" min="1" />
          </label>
        </div>

        <div class="button-row">
          <button type="button" class="button button--accent" @click="refreshList">Search</button>
        </div>
      </article>

      <article class="panel panel-stack">
        <PanelHeading eyebrow="Advanced search" title="Custom filter" />

        <label class="form-field form-field--wide">
          <span class="form-label">Filter</span>
          <textarea v-model="queryText" class="text-area" spellcheck="false" />
        </label>

        <div class="button-row">
          <button type="button" class="button" @click="runAdvancedQuery">Run filter</button>
        </div>
      </article>
    </section>

    <section class="panel panel-stack">
      <PanelHeading eyebrow="Results" :title="resultMode === 'list' ? 'Conversations' : 'Filtered results'">
        <template #aside>
          <span v-if="result" class="pill">{{ result.docs_quantity }} conversations</span>
        </template>
      </PanelHeading>

      <p v-if="loading" class="muted-copy">Loading...</p>
      <p v-else-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>
      <p v-else-if="!result || result.docs.length === 0" class="muted-copy">
        No conversations found.
      </p>

      <ul v-else class="list list-block-spacing">
        <li v-for="record in result.docs" :key="record.id" class="list-row">
          <div class="split-topline">
            <div>
              <strong>Conversation {{ record.id }}</strong>
              <p class="mono-copy">{{ record.id }}</p>
            </div>
            <span class="tag">{{ record.item_count }} items</span>
          </div>

          <div class="tag-row">
            <span class="tag">{{ record.trigger }}</span>
            <span class="tag">{{ record.status }}</span>
            <span class="tag">Created {{ formatDate(record.created_at) }}</span>
          </div>

          <RouterLink :to="`/resources/conversations/${record.id}`" class="list-link">
            Open conversation
          </RouterLink>
        </li>
      </ul>
    </section>
  </section>
</template>