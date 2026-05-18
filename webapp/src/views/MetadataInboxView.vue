<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError, createApiClient } from "../api";
import FormField from "../components/FormField.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PageHeader from "../components/PageHeader.vue";
import PanelHeading from "../components/PanelHeading.vue";
import { formatDate } from "../formatters";
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
    <PageHeader
      variant="hero"
      eyebrow="Annotations"
      title="Replay annotations"
      intro="Browse, filter, and manage replay annotations."
    >
      <template #actions>
        <RouterLink to="/resources/metadata/new" class="button button--accent">
          New annotation
        </RouterLink>
      </template>
    </PageHeader>

    <section class="results-grid">
      <article class="panel panel-stack">
        <PanelHeading eyebrow="Filters" title="Browse annotations" />

        <div class="form-grid">
          <FormField label="Replay">
            <input v-model="filters.replay" class="text-input mono-copy" type="text" />
          </FormField>

          <FormField label="Tag">
            <input v-model="filters.tag" class="text-input" type="text" />
          </FormField>

          <FormField label="Has summary">
            <select v-model="filters.hasSummary" class="select-input">
              <option value="any">Any</option>
              <option value="true">Has summary</option>
              <option value="false">No summary</option>
            </select>
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
      <PanelHeading eyebrow="Results" :title="resultMode === 'list' ? 'Annotations' : 'Filtered results'">
        <template #aside>
          <span v-if="result" class="pill">{{ result.docs_quantity }} annotations</span>
        </template>
      </PanelHeading>

      <LoadingErrorEmpty :loading="loading" :error="errorMessage" :empty="!result || result.docs.length === 0" loading-message="Loading..." empty-message="No annotations found.">
        <ul class="list list-block-spacing">
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
      </LoadingErrorEmpty>
    </section>
  </section>
</template>