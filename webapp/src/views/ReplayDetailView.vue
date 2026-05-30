<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { ApiError, createApiClient } from "../api";
import BuildOrderSequence from "../components/BuildOrderSequence.vue";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PanelHeading from "../components/PanelHeading.vue";
import PageHeader from "../components/PageHeader.vue";
import { formatCount, formatDate, formatDuration, replayRaceTagClass, replayResultClass } from "../formatters";
import { loadPlayerPortraitMetadataMap } from "../players";
import { loadReplayDetail } from "../replays";
import type { KeyValueItem } from "../components/KeyValueGrid.vue";
import type {
  MetadataRecord,
  PlayerPortraitMetadataRecord,
  ReplayDetailPlayer,
  ReplayPlayerRelationship,
  ReplayRecord,
} from "../types";

const apiClient = createApiClient();
const route = useRoute();

const leagueLabels: Record<number, string> = {
  0: "Bronze",
  1: "Silver",
  2: "Gold",
  3: "Platinum",
  4: "Diamond",
  5: "Master",
  6: "Grandmaster",
};

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const replay = ref<ReplayRecord | null>(null);
const metadata = ref<MetadataRecord | null>(null);
const players = ref<ReplayPlayerRelationship[]>([]);
const portraits = ref<Record<string, PlayerPortraitMetadataRecord>>({});
const mapImageMissing = ref(false);

const replayId = computed(() => String(route.params.replayId ?? ""));

const mapImageUrl = computed(() => {
  if (!replay.value?.map_name) return null;
  const filename = replay.value.map_name.replace(/ /g, "_").replace(/[^A-Za-z0-9._+-]/g, "_");
  return `/assets/sc2-maps/${filename}.jpg`;
});

const replayItems = computed(() => {
  if (!replay.value) return [];

  return [
    {
      label: "Winner",
      value: winner.value?.name ?? "Unknown",
      valueClass: winnerIdx.value >= 0 ? `player--p${winnerIdx.value + 1}` : undefined,
    },
    {
      label: "Date",
      value: formatDate(replay.value.date),
    },
    { label: "Map", value: replay.value.map_name },
    { label: "Region", value: replay.value.region },
    {
      label: "Length",
      value: formatDuration(replay.value.real_length),
    },
  ];
});

const winner = computed(() => {
  if (!replay.value) return null;
  return replay.value.players.find((player) => player.result === "Win") ?? null;
});

const winnerIdx = computed(() => {
  if (!replay.value || !winner.value) return -1;
  return replay.value.players.indexOf(winner.value);
});

const playerPanels = computed(() => {
  if (!replay.value) return [];

  const relationsByToonHandle = new Map(
    players.value.map((relation) => [relation.replay_player.toon_handle, relation]),
  );

  return replay.value.players.map((replayPlayer, idx) => {
    const relation = relationsByToonHandle.get(replayPlayer.toon_handle) ?? null;

    return {
      idx,
      replayPlayer,
      scalarItems: scalarItemsForPlayer(replayPlayer),
      playerInfo: relation?.player_info ?? null,
      portraitUrl: primaryPortraitUrl(replayPlayer.toon_handle),
    };
  });
});

function formatPlayerScalarNumber(value: number): string {
  return Number.isInteger(value) ? formatCount(value) : value.toFixed(1);
}

function formatLeagueLabel(league: number): string {
  return leagueLabels[league] ?? String(league);
}

function scalarItemsForPlayer(player: ReplayDetailPlayer): KeyValueItem[] {
  const items: Array<KeyValueItem | null> = [
    { label: "Name", value: player.name },
    { label: "Play race", value: player.play_race },
    { label: "Pick race", value: player.pick_race ?? "Unknown" },
    { label: "Result", value: player.result },
    player.scaled_rating != null
      ? { label: "MMR", value: formatCount(player.scaled_rating) }
      : null,
    player.avg_apm != null
      ? { label: "Avg APM", value: formatPlayerScalarNumber(player.avg_apm) }
      : null,
    player.official_apm != null
      ? { label: "Official APM", value: formatPlayerScalarNumber(player.official_apm) }
      : null,
    player.avg_sq != null
      ? { label: "Avg SQ", value: formatPlayerScalarNumber(player.avg_sq) }
      : null,
    player.highest_league != null
      ? { label: "Highest league", value: formatLeagueLabel(player.highest_league) }
      : null,
    player.clock_position != null
      ? { label: "Clock", value: `${player.clock_position} o'clock` }
      : null,
    player.clan_tag
      ? { label: "Clan tag", value: player.clan_tag }
      : null,
  ];

  return items.filter((item): item is KeyValueItem => item !== null);
}

function primaryPortraitUrl(toonHandle: string): string | null {
  const md = portraits.value[toonHandle];
  if (!md) return null;
  if (md.portrait.available) return md.portrait.url;
  if (md.portrait_constructed.available) return md.portrait_constructed.url;
  return null;
}

watch(
  replayId,
  async (value) => {
    loading.value = true;
    errorMessage.value = null;
    mapImageMissing.value = false;

    try {
      const detail = await loadReplayDetail(apiClient, value);
      replay.value = detail.replay;
      metadata.value = detail.metadata;
      players.value = detail.players;
      try {
        portraits.value = await loadPlayerPortraitMetadataMap(
          apiClient,
          detail.players.map((player) => player.replay_player.toon_handle),
        );
      } catch {
        portraits.value = {};
      }
    } catch (error) {
      errorMessage.value =
        error instanceof ApiError ? error.message : "Unable to load replay detail.";
      replay.value = null;
      metadata.value = null;
      players.value = [];
    } finally {
      loading.value = false;
    }
  },
  { immediate: true },
);
</script>

<template>
  <section class="page replay-detail-page">
    <PageHeader
      :title="replay ? replay.map_name : 'Replay detail'"
      breadcrumb-label="← Replays"
      breadcrumb-to="/replays"
    >
      <template #actions>
        <div v-if="replay" class="button-row">
          <RouterLink :to="`/resources/replays/${replay.id}`" class="button button--ghost">
            Maintenance
          </RouterLink>
        </div>
      </template>
    </PageHeader>

    <LoadingErrorEmpty :loading="loading" :error="errorMessage" loading-message="Loading…" error-class="muted-copy error-copy">
      <template v-if="replay">
      <section class="detail-grid">
        <article class="panel">
          <PanelHeading eyebrow="Replay overview" title="Metrics" />
          <KeyValueGrid class="list-block-spacing" :items="replayItems" />
        </article>

        <article class="panel panel-stack">
          <div class="map-preview-card">
            <img
              v-if="mapImageUrl && !mapImageMissing"
              :src="mapImageUrl"
              :alt="`${replay.map_name} map`"
              class="map-preview-card__image"
              @error="mapImageMissing = true"
            />
            <div v-else class="feature-surface">
              <span class="eyebrow">Map preview</span>
              <strong class="feature-surface__title">{{ replay.map_name }}</strong>
            </div>
          </div>
        </article>
      </section>

      <article class="panel panel-stack">
        <PanelHeading eyebrow="Notes" title="Game Summary" />

        <template v-if="metadata">
          <div
            v-if="metadata.description || (metadata.tags && metadata.tags.length)"
            class="replay-summary-content"
          >
            <p v-if="metadata.description" class="metadata-desc">{{ metadata.description }}</p>

            <div v-if="metadata.tags && metadata.tags.length" class="tag-row replay-summary-tags">
              <span v-for="tag in metadata.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>
          </div>
          <p v-else class="muted-copy">No description recorded.</p>

          <RouterLink v-if="metadata.replay_summary_conversation" :to="`/conversations/${metadata.replay_summary_conversation}`" class="button button--ghost">
            View summary conversation →
          </RouterLink>
        </template>

        <p v-else class="muted-copy">No metadata exists for this replay.</p>
      </article>

      <article class="panel panel-stack">
        <div class="replay-duel-grid">
          <article
            v-for="panel in playerPanels"
            :key="panel.replayPlayer.toon_handle"
            class="duel-player-card surface-card"
            :class="[
              `duel-player-card--p${panel.idx + 1}`,
              { 'surface-card--interactive': panel.playerInfo },
            ]"
          >
            <RouterLink
              v-if="panel.playerInfo"
              :to="`/players/${panel.replayPlayer.toon_handle}`"
              class="duel-player-card__overlay"
              :aria-label="`View ${panel.replayPlayer.name}`"
            />

            <div class="duel-player-card__topline">
              <span class="tag" :class="replayResultClass(panel.replayPlayer.result)">
                {{ panel.replayPlayer.result }}
              </span>
            </div>

            <div class="duel-player-card__body">
              <div class="duel-player-card__portrait">
                <img
                  v-if="panel.portraitUrl"
                  :src="panel.portraitUrl"
                  :alt="`${panel.replayPlayer.name} portrait`"
                  class="duel-player-card__portrait-img"
                />
                <div v-else class="duel-player-card__portrait-fallback">{{ panel.replayPlayer.name.slice(0, 1) }}</div>
              </div>

              <div class="duel-player-card__identity">
                <strong class="duel-player-card__name" :class="`player--p${panel.idx + 1}`">
                  {{ panel.replayPlayer.name }}
                </strong>
                <p class="duel-player-card__toon">{{ panel.replayPlayer.toon_handle }}</p>

                <div class="tag-row">
                  <span class="tag" :class="replayRaceTagClass(panel.replayPlayer.play_race)">
                    {{ panel.replayPlayer.play_race }}
                  </span>
                  <span v-if="panel.replayPlayer.scaled_rating" class="tag">
                    MMR {{ formatCount(panel.replayPlayer.scaled_rating) }}
                  </span>
                </div>
              </div>
            </div>

            <KeyValueGrid
              v-if="panel.scalarItems.length"
              class="duel-player-card__scalars"
              :items="panel.scalarItems"
            />

            <BuildOrderSequence
              :entries="panel.replayPlayer.build_order"
              :player-name="panel.replayPlayer.name"
              :player-index="panel.idx + 1"
            />
          </article>
        </div>
      </article>
      </template>
    </LoadingErrorEmpty>
  </section>
</template>

<style scoped>
.replay-detail-page :deep(.page-header) {
  align-items: flex-start;
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: flex-end;
  gap: 12px;
}

.metadata-desc {
  margin: 0;
  line-height: 1.65;
  color: var(--text-dim);
}

.replay-summary-content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 280px);
  gap: 16px;
  align-items: start;
}

.replay-summary-tags {
  width: 100%;
  justify-content: flex-end;
  align-content: start;
}

.map-preview-card {
  display: grid;
  gap: 16px;
}

.map-preview-card__image {
  display: block;
  width: 100%;
  height: auto;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}

.replay-duel-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: 16px;
}

.duel-player-card {
  position: relative;
  display: grid;
  gap: 18px;
  padding: 18px;
}

.duel-player-card--p1 {
  border-left: 2px solid var(--p1);
}

.duel-player-card--p2 {
  border-left: 2px solid var(--p2);
}

.duel-player-card__overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
}

.duel-player-card__topline {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
}

.duel-player-card__body {
  position: relative;
  z-index: 3;
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 16px;
  align-items: center;
}

.duel-player-card__portrait {
  width: 88px;
  height: 88px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(16, 24, 38, 0.9), rgba(10, 16, 26, 1));
}

.duel-player-card__portrait-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.duel-player-card__portrait-fallback {
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
  color: var(--text-muted);
  font-family: var(--display);
  font-size: 1.8rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.duel-player-card__identity {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.duel-player-card__name {
  font-family: var(--display);
  font-size: 1.2rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.duel-player-card__toon {
  margin: -4px 0 0;
  color: var(--text-muted);
  font-size: 0.8rem;
  overflow-wrap: anywhere;
}

.duel-player-card__scalars {
  position: relative;
  z-index: 3;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.duel-player-card__scalars :deep(.data-card) {
  min-width: 0;
}

.duel-player-card__scalars :deep(dd) {
  font-size: 0.95rem;
  overflow-wrap: anywhere;
}

@media (max-width: 900px) {
  .page-header__actions {
    width: 100%;
    justify-content: flex-start;
  }

  .replay-summary-content {
    grid-template-columns: 1fr;
  }

  .replay-summary-tags {
    justify-content: flex-start;
  }

  .replay-duel-grid {
    grid-template-columns: 1fr;
  }

  .duel-player-card__scalars {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .duel-player-card__body {
    grid-template-columns: 1fr;
  }

  .duel-player-card__scalars {
    grid-template-columns: 1fr;
  }

  .duel-player-card__portrait {
    width: 72px;
    height: 72px;
  }
}
</style>
