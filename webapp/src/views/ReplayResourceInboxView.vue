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
        <p class="eyebrow">Replay maintenance</p>
        <h2 class="page-hero__title">Generic replay CRUD stays separate from curated review</h2>
        <p class="panel-intro">
          Use this expert maintenance surface to create, query, patch, replace, or delete replay
          documents without collapsing the operator replay-review path into a generic editor. Raw
          JSON requests are allowed, but replay writes must still validate as a Replay.
        </p>
      </div>

      <div class="button-row">
        <RouterLink to="/replays" class="button button--ghost">Back to replay review</RouterLink>
        <RouterLink to="/resources/replays/new" class="button button--accent">
          Create replay
        </RouterLink>
      </div>
    </header>

    <section class="results-grid">
      <article class="panel panel-stack">
        <PanelHeading eyebrow="List filters" title="Replay inbox controls">
          <template #aside>
            <span class="pill">GET /api/replays</span>
          </template>
        </PanelHeading>

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
        </div>
      </article>

      <article class="panel panel-stack">
        <PanelHeading eyebrow="Advanced query" title="Read-only replay query body">
          <template #aside>
            <span class="pill">POST /api/replays/query</span>
          </template>
        </PanelHeading>

        <label class="form-field form-field--wide">
          <span class="form-label">Query JSON</span>
          <textarea v-model="queryText" class="text-area" spellcheck="false" />
        </label>

        <div class="button-row">
          <button type="button" class="button" @click="runAdvancedQuery">Run query</button>
        </div>
      </article>
    </section>

    <section class="panel panel-stack">
      <PanelHeading eyebrow="Results" :title="resultMode === 'list' ? 'Replay list results' : 'Replay query results'">
        <template #aside>
          <span v-if="result" class="pill">{{ result.docs_quantity }} replays</span>
        </template>
      </PanelHeading>

      <p v-if="loading" class="muted-copy">Loading replay maintenance results...</p>
      <p v-else-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>
      <p v-else-if="!result || result.docs.length === 0" class="muted-copy">
        No replay documents matched the current request.
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
            Open replay document
          </RouterLink>
        </li>
      </ul>
    </section>
  </section>
</template>