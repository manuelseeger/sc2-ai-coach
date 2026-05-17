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
        <p class="eyebrow">Conversation maintenance</p>
        <h2 class="page-hero__title">Writable conversation documents</h2>
        <p class="panel-intro">
          Generic maintenance stays on the top-level conversation documents. Transcript items remain append-only through the conversation-scoped API route and are not editable here.
        </p>
      </div>

      <div class="button-row">
        <span class="pill pill--accent">Writable resource</span>
        <RouterLink to="/resources/conversations/new" class="button button--accent">
          Create conversation
        </RouterLink>
      </div>
    </header>

    <section class="results-grid">
      <article class="panel panel-stack">
        <PanelHeading eyebrow="List filters" title="Reviewable browser controls">
          <template #aside>
            <span class="pill">GET /api/conversations</span>
          </template>
        </PanelHeading>

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
            <span class="form-label">Current page</span>
            <input v-model.number="filters.currentPage" class="text-input" type="number" min="1" />
          </label>

          <label class="form-field">
            <span class="form-label">Docs per page</span>
            <input v-model.number="filters.docsPerPage" class="text-input" type="number" min="1" />
          </label>
        </div>

        <div class="button-row">
          <button type="button" class="button button--accent" @click="refreshList">Run list</button>
          <span class="pill pill--amber">Typed filters</span>
        </div>
      </article>

      <article class="panel panel-stack">
        <PanelHeading eyebrow="Advanced query" title="Guarded JSON filter body">
          <template #aside>
            <span class="pill">POST /api/conversations/query</span>
          </template>
        </PanelHeading>

        <label class="form-field form-field--wide">
          <span class="form-label">Query JSON</span>
          <textarea v-model="queryText" class="text-area" spellcheck="false" />
        </label>

        <div class="button-row">
          <button type="button" class="button" @click="runAdvancedQuery">Run query</button>
          <span class="pill">Read-only query endpoint</span>
        </div>
      </article>
    </section>

    <section class="panel panel-stack">
      <PanelHeading eyebrow="Results" :title="resultMode === 'list' ? 'List results' : 'Advanced query results'">
        <template #aside>
          <span v-if="result" class="pill">{{ result.docs_quantity }} records</span>
        </template>
      </PanelHeading>

      <p v-if="loading" class="muted-copy">Loading conversation records...</p>
      <p v-else-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>
      <p v-else-if="!result || result.docs.length === 0" class="muted-copy">
        No conversation records matched the current request.
      </p>

      <ul v-else class="list list-block-spacing">
        <li v-for="record in result.docs" :key="record.id" class="list-row">
          <div class="split-topline">
            <div>
              <strong>{{ record.title || "Untitled conversation" }}</strong>
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
            Open conversation detail
          </RouterLink>
        </li>
      </ul>
    </section>
  </section>
</template>