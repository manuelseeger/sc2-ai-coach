<template>
  <section class="page-shell">
    <header class="page-header">
      <div>
        <p class="eyebrow">Reporting</p>
        <h1>Map stats</h1>
        <p class="page-copy">Read-only reporting surface for aggregation-backed replay stats.</p>
      </div>
      <div class="page-meta">
        <span>Read-only reporting surface</span>
        <span v-if="resource">{{ resource.available ? 'Available' : 'Unavailable' }}</span>
      </div>
    </header>

    <p v-if="state.loading" class="panel-copy">Loading map stats…</p>
    <p v-else-if="state.error" class="panel-error">{{ state.error }}</p>

    <section v-else-if="resource && !resource.available" class="panel panel--warning">
      <h2>Unavailable</h2>
      <p class="panel-copy">{{ resource.unavailable_reason }}</p>
    </section>

    <template v-else>
      <form class="filters" @submit.prevent="applyFilters">
        <label class="filter-control">
          <span>Map</span>
          <select v-model="state.selectedMap">
            <option value="">All maps</option>
            <option v-for="item in state.items" :key="item.map" :value="item.map">
              {{ item.map }}
            </option>
          </select>
        </label>

        <label class="filter-control">
          <span>From date</span>
          <input v-model="state.fromDate" name="from-date" type="date">
        </label>

        <label class="filter-control">
          <span>To date</span>
          <input v-model="state.toDate" name="to-date" type="date">
        </label>

        <button class="action-button" type="submit">Apply filters</button>
      </form>

      <section class="panel">
        <header class="panel-header">
          <h2>Map summaries</h2>
          <p class="panel-copy">Practical read-only review over discovered replay aggregates.</p>
        </header>

        <p v-if="state.items.length === 0" class="panel-copy">No map stats matched the current filters.</p>

        <div v-else class="summary-grid">
          <article v-for="item in state.items" :key="item.map" class="summary-card">
            <header>
              <h3>{{ item.map }}</h3>
              <span>{{ formatPercent(item.winrate) }}</span>
            </header>
            <dl class="summary-facts">
              <div>
                <dt>Games</dt>
                <dd>{{ item.games }}</dd>
              </div>
              <div>
                <dt>Record</dt>
                <dd>{{ item.wins }}-{{ item.losses }}</dd>
              </div>
            </dl>
            <ul class="matchup-list">
              <li v-for="matchup in item.matchups" :key="`${item.map}-${matchup.matchup}`">
                <strong>{{ matchup.matchup }}</strong>
                <span>{{ matchup.wins }}-{{ matchup.losses }}</span>
              </li>
            </ul>
          </article>
        </div>
      </section>

      <section v-if="state.rangeSummary !== null" class="panel">
        <header class="panel-header">
          <h2>Range comparison</h2>
          <p class="panel-copy">Named ranges keep season and same-day context visible for the selected map.</p>
        </header>

        <div class="range-grid">
          <article v-for="range in state.rangeSummary.ranges" :key="range.name" class="range-card">
            <h3>{{ formatRangeName(range.name) }}</h3>
            <p class="panel-copy">{{ range.stats ? `${range.stats.wins}-${range.stats.losses}` : 'No matches' }}</p>
            <p v-if="range.stats" class="range-winrate">{{ formatPercent(range.stats.winrate) }}</p>
          </article>
        </div>
      </section>

      <section class="panel">
        <header class="panel-header">
          <h2>Grouped results</h2>
          <p class="panel-copy">Guarded aggregation query output grouped by map and matchup.</p>
        </header>

        <div class="group-table" role="table" aria-label="Grouped map stats results">
          <div class="group-table__header" role="row">
            <span role="columnheader">Map</span>
            <span role="columnheader">Matchup</span>
            <span role="columnheader">Games</span>
            <span role="columnheader">Record</span>
            <span role="columnheader">Winrate</span>
          </div>
          <div v-for="group in state.grouped.groups" :key="groupKey(group)" class="group-table__row" role="row">
            <span role="cell">{{ group.key.map }}</span>
            <span role="cell">{{ group.key.matchup }}</span>
            <span role="cell">{{ group.games ?? 0 }}</span>
            <span role="cell">{{ group.wins ?? 0 }}-{{ group.losses ?? 0 }}</span>
            <span role="cell">{{ formatPercent(group.winrate ?? 0) }}</span>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { useAdminApi } from '../api'
import type {
  MapStatsNamedRange,
  MapStatsQueryGroup,
  MapStatsQueryResponse,
  MapStatsRangesResponse,
  MapStatsSummary,
  ResourceDiscoveryEntry,
} from '../types'

const client = useAdminApi()

const resource = ref<ResourceDiscoveryEntry | null>(null)
const state = reactive({
  loading: true,
  error: '',
  items: [] as MapStatsSummary[],
  selectedMap: '',
  fromDate: '',
  toDate: '',
  rangeSummary: null as MapStatsRangesResponse | null,
  grouped: {
    filter: {},
    date_range: { from_date: null, to_date: null },
    group_by: ['map', 'matchup'],
    metrics: ['games', 'wins', 'losses', 'winrate'],
    groups: [],
    pipeline: null,
  } as MapStatsQueryResponse,
})

onMounted(async () => {
  state.loading = true
  try {
    const resources = await client.listResources()
    resource.value = resources.find((entry) => entry.name === 'map-stats') ?? null
    if (resource.value === null) {
      state.error = 'Map stats resource is not declared by discovery.'
      return
    }
    if (!resource.value.available) {
      return
    }
    await loadReports({ map: null, fromDate: null, toDate: null })
  } catch (error) {
    state.error = error instanceof Error ? error.message : 'Unable to load map stats.'
  } finally {
    state.loading = false
  }
})

async function applyFilters(): Promise<void> {
  state.loading = true
  state.error = ''
  try {
    await loadReports({
      map: state.selectedMap.length > 0 ? state.selectedMap : null,
      fromDate: startOfDayIso(state.fromDate),
      toDate: endOfDayIso(state.toDate),
    })
  } catch (error) {
    state.error = error instanceof Error ? error.message : 'Unable to refresh map stats.'
  } finally {
    state.loading = false
  }
}

async function loadReports(params: {
  map: string | null
  fromDate: string | null
  toDate: string | null
}): Promise<void> {
  const listResponse = await client.listMapStats(params)
  state.items = listResponse.items
  state.selectedMap = listResponse.selected_map ?? params.map ?? ''
  state.grouped = await client.queryMapStats(buildQueryRequest(params))
  state.rangeSummary = null

  if (state.selectedMap.length > 0) {
    state.rangeSummary = await client.getMapStatsRanges(state.selectedMap, buildNamedRanges(params))
  }
}

function buildQueryRequest(params: {
  map: string | null
  fromDate: string | null
  toDate: string | null
}): {
  filter: Record<string, unknown>
  date_range: { from_date: string | null; to_date: string | null }
  ranges: MapStatsNamedRange[]
  group_by: string[]
  metrics: string[]
  sort: Record<string, number>
  limit: number
  include_pipeline: boolean
} {
  return {
    filter: params.map === null ? {} : { map_name: { $in: [params.map] } },
    date_range: {
      from_date: params.fromDate,
      to_date: params.toDate,
    },
    ranges: params.map === null ? [] : buildNamedRanges(params),
    group_by: ['map', 'matchup'],
    metrics: ['games', 'wins', 'losses', 'winrate'],
    sort: { games: -1 },
    limit: 20,
    include_pipeline: false,
  }
}

function buildNamedRanges(params: {
  map: string | null
  fromDate: string | null
  toDate: string | null
}): MapStatsNamedRange[] {
  const seasonStart = params.fromDate ?? startOfDayIso(state.fromDate)
  const todayStart = params.toDate === null ? null : `${params.toDate.slice(0, 10)}T00:00:00Z`
  if (seasonStart === null) {
    return []
  }
  return [
    { name: 'season', from_date: seasonStart, to_date: null },
    { name: 'today', from_date: todayStart ?? seasonStart, to_date: null },
  ]
}

function startOfDayIso(value: string): string | null {
  return value.length > 0 ? `${value}T00:00:00Z` : null
}

function endOfDayIso(value: string): string | null {
  return value.length > 0 ? `${value}T23:59:59Z` : null
}

function formatPercent(value: number): string {
  return `${Math.round(value)}%`
}

function formatRangeName(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function groupKey(group: MapStatsQueryGroup): string {
  return `${group.key.map ?? ''}-${group.key.matchup ?? ''}`
}
</script>

<style scoped>
.page-shell {
  display: grid;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: end;
}

.eyebrow {
  margin: 0 0 0.4rem;
  color: #8c3d1f;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

h1,
h2,
h3 {
  margin: 0;
}

.page-copy,
.panel-copy,
.panel-error,
.page-meta {
  margin: 0;
  color: #52606d;
}

.page-meta {
  display: grid;
  gap: 0.25rem;
  justify-items: end;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid #d9cbb9;
  border-radius: 1rem;
  background: rgba(255, 250, 242, 0.85);
}

.filter-control {
  display: grid;
  gap: 0.5rem;
}

.filter-control span {
  font-size: 0.9rem;
  font-weight: 700;
}

.filter-control select,
.filter-control input {
  min-width: 14rem;
  padding: 0.7rem 0.8rem;
  border: 1px solid #d9cbb9;
  border-radius: 0.7rem;
  background: #fffaf2;
}

.action-button {
  align-self: end;
  padding: 0.75rem 1rem;
  border: 0;
  border-radius: 999px;
  background: #8c3d1f;
  color: #fffaf2;
  font: inherit;
  cursor: pointer;
}

.panel {
  display: grid;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid #d9cbb9;
  border-radius: 1rem;
  background: #fffaf2;
}

.panel--warning {
  border-color: #c77356;
}

.panel-header {
  display: grid;
  gap: 0.35rem;
}

.summary-grid,
.range-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.summary-card,
.range-card {
  display: grid;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid #e3d5c3;
  border-radius: 0.9rem;
  background: #fcf7ef;
}

.summary-card header {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
}

.summary-facts {
  display: flex;
  gap: 1rem;
  margin: 0;
}

.summary-facts div {
  display: grid;
  gap: 0.2rem;
}

.summary-facts dt {
  color: #52606d;
  font-size: 0.85rem;
}

.summary-facts dd {
  margin: 0;
}

.matchup-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.5rem;
}

.matchup-list li {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.range-winrate {
  margin: 0;
  color: #8c3d1f;
  font-weight: 700;
}

.group-table {
  display: grid;
  gap: 0.5rem;
}

.group-table__header,
.group-table__row {
  display: grid;
  grid-template-columns: minmax(0, 2fr) repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  align-items: center;
}

.group-table__header {
  font-weight: 700;
  color: #52606d;
}

.group-table__row {
  padding: 0.75rem 0;
  border-top: 1px solid #efe2d0;
}

@media (max-width: 720px) {
  .page-header {
    flex-direction: column;
    align-items: start;
  }

  .page-meta {
    justify-items: start;
  }

  .group-table__header,
  .group-table__row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>