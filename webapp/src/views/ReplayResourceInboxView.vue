<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError, createApiClient } from "../api";
import PanelHeading from "../components/PanelHeading.vue";
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
    <header class="panel page-hero">
      <div>
        <p class="eyebrow">Replay management</p>
        <h2 class="page-hero__title">Browse and manage replays</h2>
        <p class="panel-intro">
          Search, edit, and manage replay records. Use the replay view for the full experience.
        </p>
      </div>

      <div class="button-row">
        <RouterLink to="/replays" class="button button--ghost">Back to replays</RouterLink>
        <RouterLink to="/resources/replays/new" class="button button--accent">
          Create replay
        </RouterLink>
      </div>
    </header>

    <section class="results-grid">
      <article class="panel panel-stack">
        <PanelHeading eyebrow="Filters" title="Browse replays" />

        <div class="form-grid">
          <label class="form-field">
            <span class="form-label">Player</span>
            <input v-model="filters.player" class="text-input" type="text" />
          </label>

          <label class="form-field">
            <span class="form-label">Map</span>
            <input v-model="filters.map" class="text-input" type="text" />
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
      <PanelHeading eyebrow="Results" :title="resultMode === 'list' ? 'Replays' : 'Filtered replays'">
        <template #aside>
          <span v-if="result" class="pill">{{ result.docs_quantity }} replays</span>
        </template>
      </PanelHeading>

      <p v-if="loading" class="muted-copy">Loading...</p>
      <p v-else-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>
      <p v-else-if="!result || result.docs.length === 0" class="muted-copy">
        No replays found.
      </p>

      <ul v-else class="list list-block-spacing">
        <li v-for="replay in result.docs" :key="replay.id" class="list-row">
          <div class="split-topline">
            <div>
              <strong>{{ replay.map_name }}</strong>
              <p class="mono-copy">{{ replay.id }}</p>
            </div>
            <span class="tag">{{ replay.filename }}</span>
          </div>

          <div class="tag-row">
            <span class="tag">{{ replay.players.length }} players</span>
            <span class="tag">{{ replay.real_type }}</span>
          </div>

          <RouterLink :to="`/resources/replays/${replay.id}`" class="list-link">
            Open replay
          </RouterLink>
        </li>
      </ul>
    </section>
  </section>
</template>