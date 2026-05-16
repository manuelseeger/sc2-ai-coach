<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError, createApiClient } from "../api";
import PanelHeading from "../components/PanelHeading.vue";
import { loadReplayInbox } from "../replays";
import type { PaginatedResponse, ReplayRecord } from "../types";

const apiClient = createApiClient();

const inbox = ref<PaginatedResponse<ReplayRecord> | null>(null);
const loading = ref(true);
const errorMessage = ref<string | null>(null);
const filters = reactive({
  player: "",
  map: "",
  sort: "-date",
  currentPage: 1,
  docsPerPage: 25,
});

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

async function refreshInbox(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;

  try {
    inbox.value = await loadReplayInbox(apiClient, {
      player: filters.player || undefined,
      map: filters.map || undefined,
      sort: filters.sort,
      current_page: filters.currentPage,
      docs_per_page: filters.docsPerPage,
    });
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Unable to load replays.";
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await refreshInbox();
});
</script>

<template>
  <section class="page replay-page">
    <header class="panel page-hero">
      <div>
        <p class="eyebrow">Replay review</p>
        <h2 class="page-hero__title">Replays with metadata and player linkage on one path</h2>
        <p class="panel-intro">
          Review persisted replays in recent-first order, narrow the inbox with operator-facing
          filters, and open a replay detail screen that keeps metadata and player relationships in
          view.
        </p>
      </div>

      <div class="button-row">
        <span class="pill pill--accent">Recent-first</span>
        <RouterLink to="/resources/replays" class="button button--ghost">
          Open replay maintenance
        </RouterLink>
      </div>
    </header>

    <section class="panel panel-stack">
      <PanelHeading eyebrow="Inbox filters" title="Operator-facing replay filters">
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
        <button type="button" class="button button--accent" @click="refreshInbox">Run inbox</button>
      </div>
    </section>

    <section class="panel panel-stack">
      <PanelHeading eyebrow="Replay inbox" title="Recent persisted replays">
        <template #aside>
          <span v-if="inbox" class="pill">{{ inbox.docs_quantity }} replays</span>
        </template>
      </PanelHeading>

      <p v-if="loading" class="muted-copy">Loading replay inbox...</p>
      <p v-else-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>
      <p v-else-if="!inbox || inbox.docs.length === 0" class="muted-copy">
        No replays matched the current request.
      </p>

      <ul v-else class="list list-block-spacing">
        <li v-for="replay in inbox.docs" :key="replay.id" class="list-row">
          <div class="split-topline">
            <div>
              <strong>{{ replay.map_name }}</strong>
              <p class="mono-copy">{{ replay.id }}</p>
            </div>
            <span class="tag">{{ formatDate(replay.date) }}</span>
          </div>

          <div class="tag-row">
            <span class="tag">{{ replay.real_type }}</span>
            <span class="tag">{{ replay.speed }}</span>
            <span class="tag">{{ replay.players.length }} players</span>
          </div>

          <p>
            {{ replay.players.map((player) => `${player.name} (${player.play_race})`).join(" vs ") }}
          </p>

          <RouterLink :to="`/replays/${replay.id}`" class="list-link">
            Open replay detail
          </RouterLink>
        </li>
      </ul>
    </section>
  </section>
</template>