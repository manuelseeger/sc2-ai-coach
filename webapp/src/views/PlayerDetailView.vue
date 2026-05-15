<template>
  <section class="detail-shell">
    <p class="eyebrow">Player Review</p>
    <header v-if="state.detail" class="detail-header">
      <div>
        <h1>{{ state.detail.name }}</h1>
        <p class="detail-copy">Canonical player identity, portraits, aliases, and related replays.</p>
      </div>
      <RouterLink class="back-link" to="/players">Back to players</RouterLink>
    </header>

    <p v-if="state.loading" class="detail-copy">Loading player…</p>
    <p v-else-if="state.error" class="detail-error">{{ state.error }}</p>

    <article v-else-if="state.detail" class="summary-card">
      <dl class="summary-facts">
        <div>
          <dt>Toon handle</dt>
          <dd>{{ state.detail.toon_handle }}</dd>
        </div>
        <div>
          <dt>Aliases</dt>
          <dd>{{ state.detail.alias_count }}</dd>
        </div>
        <div>
          <dt>Tags</dt>
          <dd>{{ state.detail.tags.length > 0 ? state.detail.tags.join(', ') : 'None' }}</dd>
        </div>
      </dl>
    </article>

    <section v-if="state.detail" class="detail-grid">
      <article class="media-card">
        <header class="section-header">
          <h2>Portrait media</h2>
          <span class="detail-copy">Dedicated media endpoints</span>
        </header>
        <div class="portrait-grid">
          <article class="portrait-card">
            <h3>Primary portrait</h3>
            <img
              v-if="state.portraitMetadata?.portrait.available && state.portraitMetadata.portrait.url"
              :src="state.portraitMetadata.portrait.url"
              :alt="`${state.detail.name} portrait`"
            />
            <p v-else class="detail-copy">No primary portrait recorded.</p>
          </article>
          <article class="portrait-card">
            <h3>Constructed portrait</h3>
            <img
              v-if="state.portraitMetadata?.portrait_constructed.available && state.portraitMetadata.portrait_constructed.url"
              :src="state.portraitMetadata.portrait_constructed.url"
              :alt="`${state.detail.name} constructed portrait`"
            />
            <p v-else class="detail-copy">No constructed portrait recorded.</p>
          </article>
        </div>
      </article>

      <article class="aliases-card">
        <header class="section-header">
          <h2>Aliases</h2>
          <span class="detail-copy">Portrait metadata stays out of the main JSON responses.</span>
        </header>
        <ol class="alias-list">
          <li v-for="alias in state.aliases" :key="alias.index" class="alias-card">
            <div>
              <h3>{{ alias.name }}</h3>
              <p class="detail-copy">
                {{ alias.seen_on ? `Last seen ${formatUtcDate(alias.seen_on)}` : 'No sighting date recorded.' }}
              </p>
            </div>
            <div v-if="alias.portraits.length > 0" class="alias-portraits">
              <img
                v-for="portrait in alias.portraits"
                :key="portrait.index"
                :src="portrait.url"
                :alt="`${alias.name} portrait ${portrait.index + 1}`"
              />
            </div>
            <p v-else class="detail-copy">No alias portraits recorded.</p>
          </li>
        </ol>
      </article>

      <article class="replays-card">
        <header class="section-header">
          <h2>Related replays</h2>
          <span class="detail-copy">Open replay review without embedding binary payloads.</span>
        </header>
        <ol class="replay-list">
          <li v-for="replay in state.relatedReplays" :key="replay.id">
            <RouterLink class="replay-link" :to="replay.detail_path">
              <strong>{{ replay.map_name }}</strong>
              <span>{{ replay.matchup }} · {{ formatUtcDate(replay.played_at) }}</span>
            </RouterLink>
          </li>
        </ol>
      </article>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { useAdminApi } from '../api'
import { formatUtcDate } from '../format'
import type {
  PlayerAliasSummary,
  PlayerDetailResponse,
  PlayerPortraitMetadataResponse,
  ReplayDetailResponse,
} from '../types'

const client = useAdminApi()
const route = useRoute()

const state = reactive({
  loading: true,
  error: '',
  detail: null as PlayerDetailResponse | null,
  aliases: [] as PlayerAliasSummary[],
  portraitMetadata: null as PlayerPortraitMetadataResponse | null,
  relatedReplays: [] as ReplayDetailResponse[],
})

onMounted(async () => {
  const toonHandle = String(route.params.toonHandle)
  state.loading = true
  state.error = ''

  try {
    const [detail, aliases, portraitMetadata, relatedReplays] = await Promise.all([
      client.getPlayerDetail(toonHandle),
      client.getPlayerAliases(toonHandle),
      client.getPlayerPortraitMetadata(toonHandle),
      client.getPlayerReplays(toonHandle),
    ])
    state.detail = detail
    state.aliases = aliases.aliases
    state.portraitMetadata = portraitMetadata
    state.relatedReplays = relatedReplays.items
  } catch (error) {
    state.error = error instanceof Error ? error.message : 'Unable to load player.'
  } finally {
    state.loading = false
  }
})
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
.section-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.detail-copy,
.detail-error,
.summary-facts dt {
  color: #52606d;
}

.detail-error {
  color: #9b2c2c;
}

.back-link,
.replay-link {
  color: #8c3d1f;
  font-weight: 700;
}

.summary-card,
.media-card,
.aliases-card,
.replays-card,
.portrait-card,
.alias-card {
  border: 1px solid #d9cbb9;
  border-radius: 1rem;
  background: #fffaf2;
}

.summary-card,
.media-card,
.aliases-card,
.replays-card {
  padding: 1.25rem;
}

.summary-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
}

.summary-facts div,
.replay-link {
  display: grid;
  gap: 0.2rem;
}

.summary-facts dd {
  margin: 0;
}

.detail-grid {
  display: grid;
  gap: 1rem;
}

.portrait-grid,
.alias-list,
.replay-list {
  display: grid;
  gap: 0.75rem;
  padding: 0;
  margin: 1rem 0 0;
  list-style: none;
}

.portrait-grid {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.portrait-card,
.alias-card {
  display: grid;
  gap: 0.75rem;
  padding: 1rem;
  background: #ffffff;
}

.portrait-card h3,
.alias-card h3,
.replays-card h2,
.aliases-card h2,
.media-card h2 {
  margin: 0;
}

.portrait-card img,
.alias-portraits img {
  max-width: 100%;
  border-radius: 0.75rem;
  border: 1px solid #d9cbb9;
}

.alias-portraits {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.alias-portraits img {
  width: 88px;
  height: 88px;
  object-fit: cover;
}

.replay-link {
  padding: 0.9rem 1rem;
  border-radius: 0.85rem;
  background: #fff3e2;
  text-decoration: none;
}

@media (max-width: 800px) {
  .detail-header,
  .section-header {
    flex-direction: column;
    align-items: start;
  }
}
</style>