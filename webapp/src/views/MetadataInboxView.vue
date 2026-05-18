<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError, createApiClient } from "../api";
import PanelHeading from "../components/PanelHeading.vue";
import { loadMetadataInbox, queryMetadataRecords } from "../metadata";
import type { ListParams, MetadataRecord, PaginatedResponse, QueryBody } from "../types";

const apiClient = createApiClient();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const result = ref<PaginatedResponse<MetadataRecord> | null>(null);
const resultMode = ref<"list" | "query">("list");

const filters = reactive({
  replay: "",
  tag: "",
  hasSummary: "any",
  sort: "-updated_at",
  currentPage: 1,
  docsPerPage: 25,
});

const queryText = ref(`{
  "filter": {
    "tags": "macro"
  },
  "sort": {
    "updated_at": -1
  },
  "current_page": 1,
  "docs_per_page": 10
}`);

function formatDate(value: string): string {
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short", hour12: false });
}

function listParams(): ListParams {
  return {
    current_page: filters.currentPage,
    docs_per_page: filters.docsPerPage,
    sort: filters.sort || undefined,
    replay: filters.replay || undefined,
    tag: filters.tag || undefined,
    has_summary:
      filters.hasSummary === "any" ? undefined : filters.hasSummary === "true",
  };
}

async function refreshList(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  resultMode.value = "list";

  try {
    result.value = await loadMetadataInbox(apiClient, listParams());
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : "Unable to load metadata records.";
  } finally {
    loading.value = false;
  }
}

async function runAdvancedQuery(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  resultMode.value = "query";

  try {
    const body = JSON.parse(queryText.value) as QueryBody;
    result.value = await queryMetadataRecords(apiClient, body);
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : "Advanced metadata query failed.";
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await refreshList();
});
</script>

<template>
  <section class="page metadata-page">
    <header class="panel page-hero">
      <div>
        <p class="eyebrow">Annotations</p>
        <h2 class="page-hero__title">Replay annotations</h2>
        <p class="panel-intro">
          Browse, filter, and manage replay annotations.
        </p>
      </div>

      <div class="button-row">
        <RouterLink to="/resources/metadata/new" class="button button--accent">
          New annotation
        </RouterLink>
      </div>
    </header>

    <section class="results-grid">
      <article class="panel panel-stack">
        <PanelHeading eyebrow="Filters" title="Browse annotations" />

        <div class="form-grid">
          <label class="form-field">
            <span class="form-label">Replay</span>
            <input v-model="filters.replay" class="text-input mono-copy" type="text" />
          </label>

          <label class="form-field">
            <span class="form-label">Tag</span>
            <input v-model="filters.tag" class="text-input" type="text" />
          </label>

          <label class="form-field">
            <span class="form-label">Has summary</span>
            <select v-model="filters.hasSummary" class="select-input">
              <option value="any">Any</option>
              <option value="true">Has summary</option>
              <option value="false">No summary</option>
            </select>
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
      <PanelHeading eyebrow="Results" :title="resultMode === 'list' ? 'Annotations' : 'Filtered results'">
        <template #aside>
          <span v-if="result" class="pill">{{ result.docs_quantity }} annotations</span>
        </template>
      </PanelHeading>

      <p v-if="loading" class="muted-copy">Loading...</p>
      <p v-else-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>
      <p v-else-if="!result || result.docs.length === 0" class="muted-copy">
        No annotations found.
      </p>

      <ul v-else class="list list-block-spacing">
        <li v-for="record in result.docs" :key="record.id" class="list-row">
          <div class="split-topline">
            <div>
              <strong>{{ record.description || "Untitled metadata" }}</strong>
              <p class="mono-copy">{{ record.id }}</p>
            </div>
            <span class="tag">{{ record.tags.length }} tags</span>
          </div>

          <div class="tag-row">
            <span class="tag mono-copy">Replay {{ record.replay }}</span>
            <span class="tag">{{ record.replay_summary_conversation ? "Has summary" : "No summary" }}</span>
            <span class="tag">Updated {{ formatDate(record.updated_at) }}</span>
          </div>

          <RouterLink :to="`/resources/metadata/${record.id}`" class="list-link">
            Open annotation
          </RouterLink>
        </li>
      </ul>
    </section>
  </section>
</template>