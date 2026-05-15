<template>
  <section class="players-shell">
    <header class="players-header">
      <div>
        <p class="eyebrow">Player Review</p>
        <h1>Known player identities</h1>
      </div>
      <p class="players-copy">
        Open a canonical player record to inspect aliases, portraits, and related replays.
      </p>
    </header>

    <p v-if="state.loading" class="players-copy">Loading player records…</p>
    <p v-else-if="state.error" class="players-error">{{ state.error }}</p>
    <p v-else-if="state.players.length === 0" class="players-copy">
      No player records are available yet.
    </p>

    <ol v-else class="player-list">
      <li v-for="player in state.players" :key="player.id">
        <RouterLink :to="player.detail_path" class="player-card">
          <div>
            <h2>{{ player.name }}</h2>
            <p class="players-copy">{{ player.toon_handle }}</p>
          </div>
          <dl class="player-facts">
            <div>
              <dt>Aliases</dt>
              <dd>{{ player.alias_count }}</dd>
            </div>
            <div>
              <dt>Last seen</dt>
              <dd>{{ player.last_seen_at ? formatUtcDate(player.last_seen_at) : 'Unknown' }}</dd>
            </div>
          </dl>
        </RouterLink>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { RouterLink } from 'vue-router'

import { useAdminApi } from '../api'
import { formatUtcDate } from '../format'
import type { PlayerListItem } from '../types'

const client = useAdminApi()

const state = reactive({
  loading: true,
  error: '',
  players: [] as PlayerListItem[],
})

onMounted(async () => {
  try {
    const response = await client.listPlayers({ page: 1, pageSize: 20, q: null, tag: null })
    state.players = response.items
  } catch (error) {
    state.error = error instanceof Error ? error.message : 'Unable to load player records.'
  } finally {
    state.loading = false
  }
})
</script>

<style scoped>
.players-shell {
  display: grid;
  gap: 1.5rem;
}

.players-header {
  display: grid;
  gap: 0.75rem;
}

.eyebrow {
  margin: 0;
  color: #8c3d1f;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.players-copy,
.players-error,
.player-facts dt {
  color: #52606d;
}

.players-error {
  color: #9b2c2c;
}

.player-list {
  display: grid;
  gap: 1rem;
  padding: 0;
  margin: 0;
  list-style: none;
}

.player-card {
  display: grid;
  gap: 0.9rem;
  padding: 1rem;
  border: 1px solid #d9cbb9;
  border-radius: 1rem;
  background: #fffaf2;
  color: inherit;
  text-decoration: none;
}

.player-card h2 {
  margin: 0;
}

.player-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.75rem;
}

.player-facts div {
  display: grid;
  gap: 0.2rem;
}

.player-facts dd {
  margin: 0;
}
</style>