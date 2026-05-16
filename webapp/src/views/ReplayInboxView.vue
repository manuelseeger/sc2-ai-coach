<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { ApiError, createApiClient } from "../api";
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
  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatLength(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = String(seconds % 60).padStart(2, "0");
  return `${m}:${s}`;
}

function matchupLabel(replay: ReplayRecord): string {
  return replay.players.map((p) => `${p.name} (${p.play_race})`).join(" vs ");
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
    <header class="page-header">
      <div>
        <p class="eyebrow">Replay review</p>
        <h2 class="page-title">Replays</h2>
      </div>
      <RouterLink to="/resources/replays" class="button button--ghost">
        Maintenance
      </RouterLink>
    </header>

    <section class="panel filter-panel">
      <div class="filter-row">
        <label class="filter-field">
          <span class="form-label">Player</span>
          <input v-model="filters.player" class="text-input" type="text" placeholder="Name…" />
        </label>

        <label class="filter-field">
          <span class="form-label">Map</span>
          <input v-model="filters.map" class="text-input" type="text" placeholder="Map name…" />
        </label>

        <label class="filter-field filter-field--narrow">
          <span class="form-label">Sort</span>
          <input v-model="filters.sort" class="text-input mono-copy" type="text" />
        </label>

        <label class="filter-field filter-field--narrow">
          <span class="form-label">Page</span>
          <input v-model.number="filters.currentPage" class="text-input" type="number" min="1" />
        </label>

        <div class="filter-field filter-field--action">
          <span class="form-label">&nbsp;</span>
          <button type="button" class="button button--accent" @click="refreshInbox">Apply</button>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Results</p>
          <h3>{{ inbox ? `${inbox.docs_quantity} replays` : "Replays" }}</h3>
        </div>
        <span v-if="inbox" class="pill">
          Page {{ inbox.current_page }} of {{ inbox.page_quantity }}
        </span>
      </div>

      <p v-if="loading" class="muted-copy list-block-spacing">Loading…</p>
      <p v-else-if="errorMessage" class="muted-copy list-block-spacing error-copy">{{ errorMessage }}</p>
      <p v-else-if="!inbox || inbox.docs.length === 0" class="muted-copy list-block-spacing">
        No replays matched the current filters.
      </p>

      <ul v-else class="list list-block-spacing">
        <li
          v-for="replay in inbox.docs"
          :key="replay.id"
          class="list-row list-row--linked replay-row"
        >
          <RouterLink :to="`/replays/${replay.id}`" class="list-row__overlay" aria-label="Open replay" />

          <div class="replay-row__main">
            <strong class="replay-row__map">{{ replay.map_name }}</strong>
            <p class="replay-row__matchup">{{ matchupLabel(replay) }}</p>
            <p class="replay-row__id mono-copy">{{ replay.id }}</p>
          </div>

          <div class="replay-row__meta">
            <span class="tag">{{ formatDate(replay.date) }}</span>
            <span class="tag">{{ replay.real_type }}</span>
            <span v-if="replay.real_length" class="tag">{{ formatLength(replay.real_length) }}</span>
          </div>
        </li>
      </ul>

      <div v-if="inbox && inbox.page_quantity > 1" class="pagination-row">
        <button
          class="button button--ghost"
          :disabled="filters.currentPage <= 1"
          @click="filters.currentPage--; refreshInbox()"
        >
          ← Prev
        </button>
        <span class="pagination-label">{{ filters.currentPage }} / {{ inbox.page_quantity }}</span>
        <button
          class="button button--ghost"
          :disabled="filters.currentPage >= inbox.page_quantity"
          @click="filters.currentPage++; refreshInbox()"
        >
          Next →
        </button>
      </div>
    </section>
  </section>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 8px;
}

.page-title {
  margin: 4px 0 0;
  font-family: var(--display);
  font-size: clamp(1.8rem, 3vw, 2.6rem);
  line-height: 0.93;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.filter-panel {
  display: grid;
  gap: 14px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 14px;
}

.filter-field {
  display: grid;
  gap: 6px;
  flex: 1 1 180px;
}

.filter-field--narrow {
  flex: 0 1 120px;
}

.filter-field--action {
  flex: 0 0 auto;
}

.replay-row {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 20px;
}

.replay-row__main {
  flex: 1;
  display: grid;
  gap: 4px;
  min-width: 0;
}

.replay-row__map {
  font-family: var(--display);
  font-size: 1rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text);
}

.replay-row__matchup {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.9rem;
}

.replay-row__id {
  margin: 0;
  font-size: 0.72rem;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.replay-row__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex-shrink: 0;
}

.pagination-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-muted);
}

.pagination-label {
  color: var(--text-muted);
  font-family: var(--display);
  font-size: 0.8rem;
  letter-spacing: 0.08em;
}
</style>
