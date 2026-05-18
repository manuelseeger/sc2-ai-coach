<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError, createApiClient } from "../api";
import FormField from "../components/FormField.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PageHeader from "../components/PageHeader.vue";
import PanelHeading from "../components/PanelHeading.vue";
import { loadConversationInbox, queryConversationRecords } from "../conversations";
import { formatDate } from "../formatters";
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
    <PageHeader
      variant="hero"
      eyebrow="Conversation management"
      title="Browse and manage conversations"
      intro="Search and manage conversation records. Messages are managed separately within each conversation."
    >
      <template #actions>
        <span class="pill pill--accent">Editable</span>
        <RouterLink to="/resources/conversations/new" class="button button--accent">
          Create conversation
        </RouterLink>
      </template>
    </PageHeader>

    <section class="results-grid">
      <article class="panel panel-stack">
        <PanelHeading eyebrow="Filters" title="Browse conversations" />

        <div class="form-grid">
          <FormField label="Session">
            <input v-model="filters.session" class="text-input mono-copy" type="text" />
          </FormField>

          <FormField label="Trigger">
            <input v-model="filters.trigger" class="text-input" type="text" />
          </FormField>

          <FormField label="Status">
            <input v-model="filters.status" class="text-input" type="text" />
          </FormField>

          <FormField label="Sort">
            <input v-model="filters.sort" class="text-input mono-copy" type="text" />
          </FormField>

          <FormField label="Page">
            <input v-model.number="filters.currentPage" class="text-input" type="number" min="1" />
          </FormField>

          <FormField label="Per page">
            <input v-model.number="filters.docsPerPage" class="text-input" type="number" min="1" />
          </FormField>
        </div>

        <div class="button-row">
          <button type="button" class="button button--accent" @click="refreshList">Search</button>
        </div>
      </article>

      <article class="panel panel-stack">
        <PanelHeading eyebrow="Advanced search" title="Custom filter" />

        <FormField class="form-field--wide" label="Filter">
          <textarea v-model="queryText" class="text-area" spellcheck="false" />
        </FormField>

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

      <LoadingErrorEmpty :loading="loading" :error="errorMessage" :empty="!result || result.docs.length === 0" loading-message="Loading..." empty-message="No conversations found.">
        <ul class="list list-block-spacing">
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
      </LoadingErrorEmpty>
    </section>
  </section>
</template>