<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import PanelHeading from "../components/PanelHeading.vue";
import type { MatchupRecord, MatchupsByMapRecord } from "../types";

const client = createApiClient();
const route = useRoute();
const router = useRouter();

const selectedMap = ref("");
const minDate = ref("");
const listLoading = ref(false);
const detailLoading = ref(false);
const listError = ref<string | null>(null);
const detailError = ref<string | null>(null);
const mapStats = ref<MatchupsByMapRecord[]>([]);
const selectedMapStats = ref<MatchupsByMapRecord | null>(null);

const mapOptions = computed(() => mapStats.value.map((entry) => entry.map));
const activeMatchups = computed<MatchupRecord[]>(() => selectedMapStats.value?.matchups ?? []);

function buildParams() {
  const params: Record<string, string> = {};
  if (minDate.value) {
    params.min_date = new Date(minDate.value).toISOString();
  }
  return params;
}

function toDateTimeLocalValue(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }

  const offsetMinutes = parsed.getTimezoneOffset();
  const localTime = new Date(parsed.getTime() - offsetMinutes * 60_000);
  return localTime.toISOString().slice(0, 16);
}

async function syncRoute() {
  const query: Record<string, string> = {};
  if (selectedMap.value) {
    query.map = selectedMap.value;
  }
  if (minDate.value) {
    query.min_date = minDate.value;
  }
  await router.replace({ query });
}

async function loadMapStats() {
  listLoading.value = true;
  listError.value = null;

  try {
    mapStats.value = await client.getMapStats<MatchupsByMapRecord[]>(buildParams());
  } catch (error) {
    mapStats.value = [];
    listError.value = error instanceof ApiError ? error.message : "Map stats request failed.";
  } finally {
    listLoading.value = false;
  }
}

async function loadSelectedMapStats() {
  if (!selectedMap.value) {
    selectedMapStats.value = null;
    detailError.value = null;
    return;
  }

  if (!mapStats.value.some((entry) => entry.map === selectedMap.value)) {
    selectedMapStats.value = null;
    detailError.value = "No grouped stats exist for the selected map under the active filters.";
    return;
  }

  detailLoading.value = true;
  detailError.value = null;

  try {
    selectedMapStats.value = await client.getMapStatsByName<MatchupsByMapRecord>(
      selectedMap.value,
      buildParams(),
    );
  } catch (error) {
    selectedMapStats.value = null;
    detailError.value = error instanceof ApiError ? error.message : "Map detail request failed.";
  } finally {
    detailLoading.value = false;
  }
}

async function applyFilters() {
  await syncRoute();
  await loadMapStats();
  await loadSelectedMapStats();
}

async function reviewMap(mapName: string) {
  selectedMap.value = mapName;
  await applyFilters();
}

async function clearFilters() {
  selectedMap.value = "";
  minDate.value = "";
  await applyFilters();
}

onMounted(async () => {
  if (typeof route.query.map === "string") {
    selectedMap.value = route.query.map;
  }
  if (typeof route.query.min_date === "string") {
    minDate.value = toDateTimeLocalValue(route.query.min_date);
  }
  await applyFilters();
});
</script>

<template>
  <section class="page map-stats-page">
    <article class="panel panel-stack">
      <PanelHeading eyebrow="Reporting" title="Map matchup stats" level="h2">
        <template #aside>
          <span class="pill pill--warn">Read only</span>
        </template>
      </PanelHeading>

      <p class="panel-intro">
        Aggregated matchup reporting backed by replay data. Only the supported exact map filter
        and inclusive lower-bound date filter are available here.
      </p>

      <form class="map-stats-filters" @submit.prevent="applyFilters">
        <label class="field-group">
          <span class="field-label">Map</span>
          <select v-model="selectedMap" class="field-input">
            <option value="">All supported maps</option>
            <option v-for="mapName in mapOptions" :key="mapName" :value="mapName">
              {{ mapName }}
            </option>
          </select>
        </label>

        <label class="field-group">
          <span class="field-label">Min date</span>
          <input v-model="minDate" class="field-input" type="datetime-local" />
        </label>

        <div class="map-stats-actions">
          <button type="submit" class="button button--primary">Apply filters</button>
          <button type="button" class="button button--ghost" @click="clearFilters">Clear</button>
        </div>
      </form>
    </article>

    <div class="map-stats-layout">
      <article class="panel panel-stack">
        <PanelHeading eyebrow="Overview" title="Maps" level="h3" />
        <p v-if="listLoading" class="list-row feedback">Loading map stats...</p>
        <p v-else-if="listError" class="list-row feedback error-copy">{{ listError }}</p>
        <p v-else-if="!mapStats.length" class="list-row feedback">
          No grouped map stats match the active filters.
        </p>
        <div v-else class="map-list">
          <button
            v-for="entry in mapStats"
            :key="entry.map"
            type="button"
            class="map-card"
            :class="{ 'map-card--active': entry.map === selectedMap }"
            @click="reviewMap(entry.map)"
          >
            <strong class="map-card__title">{{ entry.map }}</strong>
            <span class="map-card__meta">{{ entry.matchups.length }} matchup rows</span>
          </button>
        </div>
      </article>

      <article class="panel panel-stack">
        <PanelHeading
          eyebrow="Detail"
          :title="selectedMapStats ? selectedMapStats.map : 'Map detail'"
          level="h3"
        />

        <p v-if="detailLoading" class="list-row feedback">Loading selected map...</p>
        <p v-else-if="detailError" class="list-row feedback error-copy">{{ detailError }}</p>
        <p v-else-if="!selectedMapStats" class="list-row feedback">
          Select a map to inspect the read-only matchup breakdown.
        </p>
        <table v-else class="table">
          <thead>
            <tr>
              <th>Matchup</th>
              <th>Games</th>
              <th>Wins</th>
              <th>Losses</th>
              <th>Win rate</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="matchup in activeMatchups" :key="matchup.matchup">
              <td>{{ matchup.matchup }}</td>
              <td>{{ matchup.totalGames }}</td>
              <td>{{ matchup.wins }}</td>
              <td>{{ matchup.losses }}</td>
              <td>{{ (matchup.winrate * 100).toFixed(1) }}%</td>
            </tr>
          </tbody>
        </table>
      </article>
    </div>
  </section>
</template>

<style scoped>
.map-stats-page {
  display: grid;
  gap: 24px;
}

.map-stats-filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  align-items: end;
}

.field-group {
  display: grid;
  gap: 8px;
}

.field-label {
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.field-input {
  width: 100%;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid var(--border-strong);
  background: rgba(8, 16, 28, 0.78);
  color: var(--text-primary);
}

.map-stats-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.button {
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  padding: 12px 18px;
  font: inherit;
  cursor: pointer;
}

.button--primary {
  background: linear-gradient(135deg, rgba(74, 222, 128, 0.2), rgba(56, 189, 248, 0.22));
  color: var(--text-primary);
}

.button--ghost {
  background: transparent;
  color: var(--text-secondary);
}

.map-stats-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.95fr) minmax(0, 1.25fr);
  gap: 24px;
}

.map-list {
  display: grid;
  gap: 12px;
}

.map-card {
  display: grid;
  gap: 4px;
  text-align: left;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid var(--border-subtle);
  background: rgba(10, 18, 30, 0.8);
  color: var(--text-primary);
  cursor: pointer;
}

.map-card--active {
  border-color: rgba(74, 222, 128, 0.45);
  box-shadow: inset 0 0 0 1px rgba(74, 222, 128, 0.2);
}

.map-card__title {
  font-size: 0.98rem;
}

.map-card__meta {
  color: var(--text-muted);
  font-size: 0.82rem;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  padding: 12px 10px;
  border-bottom: 1px solid var(--border-subtle);
  text-align: left;
}

@media (max-width: 900px) {
  .map-stats-filters,
  .map-stats-layout {
    grid-template-columns: 1fr;
  }

  .map-stats-actions {
    justify-content: flex-start;
  }
}
</style>