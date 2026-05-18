<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { ApiError, createApiClient } from "../api";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import PanelHeading from "../components/PanelHeading.vue";
import { loadPlayerPortraitMetadataMap } from "../players";
import { loadReplayDetail } from "../replays";
import type { MetadataRecord, PlayerPortraitMetadataRecord, ReplayPlayerRelationship, ReplayRecord } from "../types";

const apiClient = createApiClient();
const route = useRoute();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const replay = ref<ReplayRecord | null>(null);
const metadata = ref<MetadataRecord | null>(null);
const players = ref<ReplayPlayerRelationship[]>([]);
const portraits = ref<Record<string, PlayerPortraitMetadataRecord>>({});

const replayId = computed(() => String(route.params.replayId ?? ""));

const replayItems = computed(() => {
  if (!replay.value) return [];

  return [
    {
      label: "Date",
      value: new Date(replay.value.date).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
        hour12: false,
      }),
    },
    { label: "Map", value: replay.value.map_name },
    { label: "Region", value: replay.value.region },
    {
      label: "Length",
      value: replay.value.real_length
        ? `${Math.floor(replay.value.real_length / 60)}:${String(replay.value.real_length % 60).padStart(2, "0")}`
        : "—",
    },
  ];
});

const winner = computed(() => {
  if (!replay.value) return null;
  return replay.value.players.find(p => p.result === "Win") ?? null;
});

const winnerIdx = computed(() => {
  if (!replay.value || !winner.value) return -1;
  return replay.value.players.indexOf(winner.value);
});

function primaryPortraitUrl(toonHandle: string): string | null {
  const md = portraits.value[toonHandle];
  if (!md) return null;
  if (md.portrait.available) return md.portrait.url;
  if (md.portrait_constructed.available) return md.portrait_constructed.url;
  return null;
}

function resultClass(result: string): string {
  if (result === "Win") return "tag--ok";
  if (result === "Loss") return "tag--warn";
  return "";
}

function raceTagClass(race: string): string {
  const map: Record<string, string> = {
    Terran: "tag--race-t",
    Protoss: "tag--race-p",
    Zerg: "tag--race-z",
    Random: "tag--race-r",
  };
  return map[race] ?? "";
}

watch(
  replayId,
  async (value) => {
    loading.value = true;
    errorMessage.value = null;

    try {
      const detail = await loadReplayDetail(apiClient, value);
      replay.value = detail.replay;
      metadata.value = detail.metadata;
      players.value = detail.players;
      try {
        portraits.value = await loadPlayerPortraitMetadataMap(
          apiClient,
          detail.players.map(p => p.replay_player.toon_handle),
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
    <header class="page-header">
      <div class="page-header__breadcrumb">
        <RouterLink to="/replays" class="breadcrumb-link">← Replays</RouterLink>
        <h2 v-if="replay" class="page-title">{{ replay.map_name }}</h2>
        <h2 v-else class="page-title">Replay detail</h2>
        <p v-if="winner" class="replay-winner">
          Winner: <span :class="`player--p${winnerIdx + 1}`">{{ winner.name }}</span>
        </p>
      </div>
      <div v-if="replay" class="button-row">
        <RouterLink :to="`/resources/replays/${replay.id}`" class="button button--ghost">
          Maintenance
        </RouterLink>
      </div>
    </header>

    <p v-if="loading" class="muted-copy">Loading…</p>
    <p v-else-if="errorMessage" class="muted-copy error-copy">{{ errorMessage }}</p>

    <template v-else-if="replay">
      <section class="detail-grid">
        <article class="panel panel-stack">
          <PanelHeading eyebrow="Replay facts" :title="replay.map_name">
            <template #aside>
              <div class="tag-row">
                <template v-for="(p, idx) in replay.players" :key="p.toon_handle">
                  <span class="tag" :class="[resultClass(p.result), `player--p${idx + 1}`]">{{ p.name }}</span>
                  <span class="tag" :class="raceTagClass(p.play_race)">{{ p.play_race }}</span>
                </template>
              </div>
            </template>
          </PanelHeading>

          <KeyValueGrid :items="replayItems" />
        </article>

        <article class="panel panel-stack">
          <PanelHeading eyebrow="Metadata" title="Replay annotation">
            <template #aside>
              <span class="pill pill--amber">Relationship route</span>
            </template>
          </PanelHeading>

          <template v-if="metadata">
            <p v-if="metadata.description" class="metadata-desc">{{ metadata.description }}</p>
            <p v-else class="muted-copy">No description recorded.</p>

            <div v-if="metadata.tags && metadata.tags.length" class="tag-row list-block-spacing">
              <span v-for="tag in metadata.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>

            <RouterLink v-if="metadata.replay_summary_conversation" :to="`/conversations/${metadata.replay_summary_conversation}`" class="button button--ghost">
              View summary conversation →
            </RouterLink>
          </template>

          <p v-else class="muted-copy">
            No metadata exists for this replay.
          </p>
        </article>
      </section>

      <article class="panel panel-stack">
        <PanelHeading eyebrow="Players" title="Participants and known identities" />

        <ul class="list list-block-spacing">
          <li
            v-for="(relation, idx) in players"
            :key="relation.replay_player.toon_handle"
            class="list-row player-row"
            :class="[`list-row--p${idx + 1}`, { 'list-row--linked': relation.player_info }]"
          >
            <RouterLink
              v-if="relation.player_info"
              :to="`/players/${relation.replay_player.toon_handle}`"
              class="list-row__overlay"
              :aria-label="`View ${relation.replay_player.name}`"
            />
            <div class="player-row__portrait">
              <img
                v-if="primaryPortraitUrl(relation.replay_player.toon_handle)"
                :src="primaryPortraitUrl(relation.replay_player.toon_handle) ?? ''"
                :alt="`${relation.replay_player.name} portrait`"
                class="player-row__portrait-img"
              />
              <div v-else class="player-row__portrait-fallback">?</div>
            </div>

            <div class="player-row__body">
              <div class="player-row__head">
                <div>
                  <strong class="player-row__name" :class="`player--p${idx + 1}`">{{ relation.replay_player.name }}</strong>
                  </div>
                <div class="tag-row">
                  <span class="tag" :class="resultClass(relation.replay_player.result)">
                    {{ relation.replay_player.result }}
                  </span>
                  <span class="tag" :class="raceTagClass(relation.replay_player.play_race)">
                    {{ relation.replay_player.play_race }}
                  </span>
                  <span v-if="relation.replay_player.scaled_rating" class="tag">
                    MMR {{ relation.replay_player.scaled_rating.toLocaleString() }}
                  </span>
                </div>
              </div>

              <div class="player-row__record">
                <span v-if="relation.player_info" class="tag tag--ok">Player record found</span>
                <span v-else class="tag tag--warn">No player record</span>
              </div>
            </div>
          </li>
        </ul>
      </article>
    </template>
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

.page-header__breadcrumb {
  display: grid;
  gap: 4px;
}

.breadcrumb-link {
  color: var(--accent);
  font-size: 0.78rem;
  font-family: var(--display);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  transition: color 150ms ease;
}

.breadcrumb-link:hover {
  color: var(--accent-strong);
}

.page-title {
  margin: 0;
  font-family: var(--display);
  font-size: clamp(1.5rem, 2.5vw, 2.2rem);
  line-height: 0.95;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.metadata-desc {
  margin: 0;
  line-height: 1.65;
  color: var(--text-dim);
}

.player-row {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 16px;
  padding: 16px 18px;
  align-items: center;
}

.player-row__portrait {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(16, 24, 38, 0.9), rgba(10, 16, 26, 1));
  flex-shrink: 0;
}

.player-row__portrait-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.player-row__portrait-fallback {
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
  color: var(--text-muted);
  font-size: 1.2rem;
}

.player-row__body {
  display: grid;
  gap: 10px;
}

.player-row__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.player-row__name {
  font-family: var(--display);
  font-size: 1rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.player-row__toon {
  margin: 4px 0 0;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.player-row__record {
  display: flex;
  align-items: center;
  gap: 10px;
}

.replay-winner {
  margin: 6px 0 0;
  font-family: var(--display);
  font-size: 1rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-dim);
}
</style>
