<template>
  <section class="detail-shell">
    <p class="eyebrow">Replay Review</p>
    <header v-if="state.detail" class="detail-header">
      <div>
        <h1>Replay review</h1>
        <p class="detail-copy">
          Replay facts, linked metadata, and known player records in one review workflow.
        </p>
      </div>
      <RouterLink class="back-link" to="/">Back to workspace</RouterLink>
    </header>

    <p v-if="state.loading" class="detail-copy">Loading replay…</p>
    <p v-else-if="state.error" class="detail-error">{{ state.error }}</p>

    <article v-else-if="state.detail" class="summary-card">
      <h2>{{ state.detail.map_name }}</h2>
      <dl class="summary-facts">
        <div>
          <dt>Replay</dt>
          <dd>{{ state.detail.id }}</dd>
        </div>
        <div>
          <dt>Played</dt>
          <dd>{{ formatUtcDate(state.detail.played_at) }}</dd>
        </div>
        <div>
          <dt>Matchup</dt>
          <dd>{{ state.detail.matchup }}</dd>
        </div>
        <div>
          <dt>Mode</dt>
          <dd>{{ state.detail.game_type }}</dd>
        </div>
        <div>
          <dt>Length</dt>
          <dd>{{ formatDuration(state.detail.real_length_seconds) }}</dd>
        </div>
        <div>
          <dt>Winner</dt>
          <dd>{{ state.detail.winning_player_name ?? 'Unknown' }}</dd>
        </div>
      </dl>
    </article>

    <section v-if="state.metadata || state.players.length > 0" class="replay-grid">
      <article class="meta-card">
        <header class="section-header">
          <h2>Replay metadata</h2>
          <RouterLink
            v-if="state.metadata?.replay_summary_conversation"
            :to="state.metadata.replay_summary_conversation.path"
            class="context-link"
          >
            Summary conversation
          </RouterLink>
        </header>
        <p class="detail-copy">
          {{ state.metadata?.description ?? 'No replay metadata has been recorded yet.' }}
        </p>
        <ul v-if="state.metadata && state.metadata.tags.length > 0" class="tag-list">
          <li v-for="tag in state.metadata.tags" :key="tag">{{ tag }}</li>
        </ul>
      </article>

      <section v-if="state.players.length > 0" class="players-card">
        <header class="section-header players-card__header">
          <div>
            <h2>Player records</h2>
            <p class="detail-copy">Jump between replay facts and the participating player records.</p>
          </div>
          <nav class="player-nav" aria-label="Replay players">
            <a
              v-for="player in state.players"
              :key="player.toon_handle"
              :href="`#${playerAnchorId(player.toon_handle)}`"
              class="player-nav__link"
            >
              {{ player.name }}
            </a>
          </nav>
        </header>

        <ol class="player-list">
          <li v-for="player in state.players" :id="playerAnchorId(player.toon_handle)" :key="player.toon_handle">
            <article class="player-card">
              <header class="player-card__header">
                <div>
                  <h3>{{ player.name }}</h3>
                  <p class="detail-copy">{{ player.toon_handle }}</p>
                </div>
                <span v-if="player.player_record" class="player-badge">Known player record</span>
              </header>

              <dl class="player-facts">
                <div>
                  <dt>Race</dt>
                  <dd>{{ player.play_race }}</dd>
                </div>
                <div>
                  <dt>Result</dt>
                  <dd>{{ player.result }}</dd>
                </div>
                <div>
                  <dt>MMR</dt>
                  <dd>{{ player.scaled_rating }}</dd>
                </div>
                <div>
                  <dt>Avg APM</dt>
                  <dd>{{ Math.round(player.avg_apm) }}</dd>
                </div>
              </dl>

              <p v-if="player.aliases.length > 0" class="alias-copy">
                Aliases: {{ player.aliases.join(', ') }}
              </p>

              <RouterLink
                v-if="player.player_record"
                class="context-link"
                :to="player.player_record.path"
              >
                Open player review
              </RouterLink>
            </article>
          </li>
        </ol>
      </section>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { useAdminApi } from '../api'
import { formatUtcDate } from '../format'
import type {
  ReplayDetailResponse,
  ReplayMetadataResponse,
  ReplayPlayerSummary,
} from '../types'

const client = useAdminApi()
const route = useRoute()

const state = reactive({
  loading: true,
  error: '',
  detail: null as ReplayDetailResponse | null,
  metadata: null as ReplayMetadataResponse | null,
  players: [] as ReplayPlayerSummary[],
})

onMounted(async () => {
  const replayId = String(route.params.replayId)
  state.loading = true
  state.error = ''

  try {
    const [detail, metadata, players] = await Promise.all([
      client.getReplayDetail(replayId),
      client.getReplayMetadata(replayId),
      client.getReplayPlayers(replayId),
    ])
    state.detail = detail
    state.metadata = metadata
    state.players = players.players
  } catch (error) {
    state.error = error instanceof Error ? error.message : 'Unable to load replay.'
  } finally {
    state.loading = false
  }
})

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}:${String(remainingSeconds).padStart(2, '0')}`
}

function playerAnchorId(toonHandle: string): string {
  return `player-${toonHandle}`
}
</script>

<style scoped>
.detail-shell {
  display: grid;
  gap: 1.5rem;
}

.eyebrow {
  margin: 0;
  color: #8c3d1f;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.detail-header,
.section-header,
.player-card__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.detail-header {
  align-items: end;
}

.detail-copy,
.detail-error,
.summary-facts dt,
.player-facts dt {
  color: #52606d;
}

.detail-error {
  color: #9b2c2c;
}

.back-link,
.context-link,
.player-nav__link {
  color: #8c3d1f;
  font-weight: 700;
}

.summary-card,
.meta-card,
.players-card,
.player-card {
  border: 1px solid #d9cbb9;
  border-radius: 1rem;
  background: #fffaf2;
}

.summary-card,
.meta-card,
.players-card {
  padding: 1.25rem;
}

.summary-card h2,
.meta-card h2,
.players-card h2,
.player-card h3 {
  margin: 0;
}

.summary-facts,
.player-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
}

.summary-facts div,
.player-facts div {
  display: grid;
  gap: 0.2rem;
}

.summary-facts dd,
.player-facts dd {
  margin: 0;
}

.replay-grid {
  display: grid;
  gap: 1rem;
}

.tag-list,
.player-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  padding: 0;
  margin: 1rem 0 0;
  list-style: none;
}

.tag-list li,
.player-nav__link,
.player-badge {
  border-radius: 999px;
  background: #fff3e2;
  color: #8c3d1f;
  font-weight: 700;
  padding: 0.35rem 0.7rem;
}

.players-card {
  display: grid;
  gap: 1rem;
}

.players-card__header {
  align-items: start;
}

.player-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.player-list {
  display: grid;
  gap: 0.75rem;
  margin-top: 0;
}

.player-card {
  display: grid;
  gap: 0.9rem;
  padding: 1rem;
  background: #ffffff;
}

.alias-copy {
  margin: 0;
  color: #52606d;
}

@media (max-width: 800px) {
  .detail-header,
  .section-header,
  .player-card__header {
    flex-direction: column;
    align-items: start;
  }
}
</style>