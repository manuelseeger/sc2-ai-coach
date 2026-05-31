<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError, createApiClient } from "../api";
import FormField from "../components/FormField.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PageHeader from "../components/PageHeader.vue";
import PanelHeading from "../components/PanelHeading.vue";
import ResourceInboxControls from "../components/ResourceInboxControls.vue";
import ResourceListRow from "../components/ResourceListRow.vue";
import { loadReplayInbox, queryReplayRecords } from "../replays";
import type { PaginatedResponse, QueryBody, ReplayRecord } from "../types";

const apiClient = createApiClient();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const result = ref<PaginatedResponse<ReplayRecord> | null>(null);
const resultMode = ref<"list" | "query">("list");

const filters = reactive({
  player: "",
  map: "",
  sort: "-date",
  currentPage: 1,
  docsPerPage: 25,
});

const queryText = ref(`{
  "filter": {
    "filename": "replay.SC2Replay"
  },
  "sort": {
    "date": -1
  },
  "current_page": 1,
  "docs_per_page": 10
}`);

async function refreshList(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  resultMode.value = "list";

  try {
    result.value = await loadReplayInbox(apiClient, {
      player: filters.player || undefined,
      map: filters.map || undefined,
      sort: filters.sort || undefined,
      current_page: filters.currentPage,
      docs_per_page: filters.docsPerPage,
    });
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Unable to load replay maintenance inbox.";
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
    result.value = await queryReplayRecords(apiClient, body);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Advanced replay query failed.";
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await refreshList();
});
</script>

<template>
  <section class="page replay-resource-page">
    <PageHeader
      variant="hero"
      eyebrow="Replay management"
      title="Browse and manage replays"
      intro="Search, edit, and manage replay records. Use the replay view for the full experience."
    >
      <template #actions>
        <RouterLink to="/replays" class="button button--ghost">Back to replays</RouterLink>
        <RouterLink to="/resources/replays/new" class="button button--accent">
          Create replay
        </RouterLink>
      </template>
    </PageHeader>

    <ResourceInboxControls
      primary-title="Browse replays"
      secondary-title="Custom filter"
      secondary-intro="Run a direct JSON query when the replay list filters are too coarse."
    >
      <template #primary>
        <div class="form-grid">
          <FormField label="Player">
            <input v-model="filters.player" class="text-input" type="text" />
          </FormField>

          <FormField label="Map">
            <input v-model="filters.map" class="text-input" type="text" />
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
      </template>

      <template #secondary>
        <FormField class="form-field--wide" label="Filter">
          <textarea v-model="queryText" class="text-area" spellcheck="false" />
        </FormField>

        <div class="button-row">
          <button type="button" class="button" @click="runAdvancedQuery">Run filter</button>
        </div>
      </template>
    </ResourceInboxControls>

    <section class="panel panel-stack">
      <PanelHeading eyebrow="Results" :title="resultMode === 'list' ? 'Replays' : 'Filtered replays'">
        <template #aside>
          <span v-if="result" class="pill">{{ result.docs_quantity }} replays</span>
        </template>
      </PanelHeading>

      <LoadingErrorEmpty :loading="loading" :error="errorMessage" :empty="!result || result.docs.length === 0" loading-message="Loading..." empty-message="No replays found.">
        <ul class="list list-block-spacing">
          <ResourceListRow
            v-for="replay in result.docs"
            :key="replay.id"
            :to="`/resources/replays/${replay.id}`"
            :title="replay.map_name"
            :summary="replay.id"
            :aria-label="`Open replay ${replay.id}`"
          >
            <template #meta>
              <span class="tag">{{ replay.players.length }} players</span>
              <span class="tag">{{ replay.real_type }}</span>
            </template>
          </ResourceListRow>
        </ul>
      </LoadingErrorEmpty>
    </section>
  </section>
</template>