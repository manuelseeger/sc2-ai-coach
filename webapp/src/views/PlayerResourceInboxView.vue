<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError, createApiClient } from "../api";
import PanelHeading from "../components/PanelHeading.vue";
import { loadPlayerInbox, queryPlayerRecords } from "../players";
import type { PaginatedResponse, PlayerInfoRecord, QueryBody } from "../types";

const apiClient = createApiClient();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const result = ref<PaginatedResponse<PlayerInfoRecord> | null>(null);
const resultMode = ref<"list" | "query">("list");

const filters = reactive({
  q: "",
  tag: "",
  sort: "name",
  currentPage: 1,
  docsPerPage: 25,
});

const queryText = ref(`{
  "filter": {
    "tags": "ladder"
  },
  "sort": {
    "name": 1
  },
  "current_page": 1,
  "docs_per_page": 10
}`);

async function refreshList(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  resultMode.value = "list";

  try {
    result.value = await loadPlayerInbox(apiClient, {
      q: filters.q || undefined,
      tag: filters.tag || undefined,
      sort: filters.sort || undefined,
      current_page: filters.currentPage,
      docs_per_page: filters.docsPerPage,
    });
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Unable to load player maintenance inbox.";
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
    result.value = await queryPlayerRecords(apiClient, body);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Advanced player query failed.";
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await refreshList();
});
</script>

<template>
  <section class="page player-resource-page">
    <header class="panel page-hero">
      <div>
        <p class="eyebrow">Player management</p>
        <h2 class="page-hero__title">Browse and manage players</h2>
        <p class="panel-intro">
          Search, edit, and manage player records.
        </p>
      </div>

      <div class="button-row">
        <RouterLink to="/players" class="button button--ghost">Back to players</RouterLink>
        <RouterLink to="/resources/players/new" class="button button--accent">Create player</RouterLink>
      </div>
    </header>

    <section class="results-grid">
      <article class="panel panel-stack">
        <PanelHeading eyebrow="Filters" title="Browse players" />

        <div class="form-grid">
          <label class="form-field">
            <span class="form-label">Search</span>
            <input v-model="filters.q" class="text-input" type="text" />
          </label>

          <label class="form-field">
            <span class="form-label">Tag</span>
            <input v-model="filters.tag" class="text-input" type="text" />
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
      <PanelHeading eyebrow="Results" :title="resultMode === 'list' ? 'Players' : 'Filtered players'">
        <template #aside>
          <span v-if="result" class="pill">{{ result.docs_quantity }} players</span>
        </template>
      </PanelHeading>

      <p v-if="loading" class="muted-copy">Loading...</p>
      <p v-else-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>
      <p v-else-if="!result || result.docs.length === 0" class="muted-copy">
        No players found.
      </p>

      <ul v-else class="list list-block-spacing">
        <li v-for="player in result.docs" :key="player.toon_handle" class="list-row">
          <div class="split-topline">
            <div>
              <strong>{{ player.name }}</strong>
              <p class="mono-copy">{{ player.toon_handle }}</p>
            </div>
            <span class="tag">{{ player.aliases.length }} aliases</span>
          </div>

          <div class="tag-row">
            <span class="tag">{{ player.tags?.length ?? 0 }} tags</span>
          </div>

          <RouterLink :to="`/resources/players/${player.toon_handle}`" class="list-link">
            Open player
          </RouterLink>
        </li>
      </ul>
    </section>
  </section>
</template>