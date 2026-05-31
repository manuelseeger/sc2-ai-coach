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
    <PageHeader
      variant="hero"
      eyebrow="Player management"
      title="Browse and manage players"
      intro="Search, edit, and manage player records."
    >
      <template #actions>
        <RouterLink to="/players" class="button button--ghost">Back to players</RouterLink>
        <RouterLink to="/resources/players/new" class="button button--accent">Create player</RouterLink>
      </template>
    </PageHeader>

    <ResourceInboxControls
      primary-title="Browse players"
      secondary-title="Custom filter"
      secondary-intro="Run a direct JSON query when tag and text filters are not enough."
    >
      <template #primary>
        <div class="form-grid">
          <FormField label="Search">
            <input v-model="filters.q" class="text-input" type="text" />
          </FormField>

          <FormField label="Tag">
            <input v-model="filters.tag" class="text-input" type="text" />
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
      <PanelHeading eyebrow="Results" :title="resultMode === 'list' ? 'Players' : 'Filtered players'">
        <template #aside>
          <span v-if="result" class="pill">{{ result.docs_quantity }} players</span>
        </template>
      </PanelHeading>

      <LoadingErrorEmpty :loading="loading" :error="errorMessage" :empty="!result || result.docs.length === 0" loading-message="Loading..." empty-message="No players found.">
        <ul class="list list-block-spacing">
          <ResourceListRow
            v-for="player in result.docs"
            :key="player.toon_handle"
            :to="`/resources/players/${player.toon_handle}`"
            :title="player.name"
            :summary="player.toon_handle"
            :aria-label="`Open player ${player.name}`"
          >
            <template #aside>
              <span class="tag">{{ player.aliases.length }} aliases</span>
            </template>
            <template #meta>
              <span class="tag">{{ player.tags?.length ?? 0 }} tags</span>
            </template>
          </ResourceListRow>
        </ul>
      </LoadingErrorEmpty>
    </section>
  </section>
</template>