<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { ApiError, createApiClient } from "../api";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import PanelHeading from "../components/PanelHeading.vue";
import { loadReplayDetail } from "../replays";
import type { MetadataRecord, ReplayPlayerRelationship, ReplayRecord } from "../types";

const apiClient = createApiClient();
const route = useRoute();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const replay = ref<ReplayRecord | null>(null);
const metadata = ref<MetadataRecord | null>(null);
const players = ref<ReplayPlayerRelationship[]>([]);

const replayId = computed(() => String(route.params.replayId ?? ""));

const replayItems = computed(() => {
  if (!replay.value) return [];

  return [
    { label: "Replay ID", value: replay.value.id, valueClass: "kv-grid__mono" },
    {
      label: "Date",
      value: new Date(replay.value.date).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }),
    },
    { label: "Map", value: replay.value.map_name },
    { label: "Filename", value: replay.value.filename },
    { label: "Region", value: replay.value.region },
    {
      label: "Length",
      value: replay.value.real_length
        ? `${Math.floor(replay.value.real_length / 60)}:${String(replay.value.real_length % 60).padStart(2, "0")}`
        : "—",
    },
    { label: "Type", value: replay.value.real_type },
    { label: "Speed", value: replay.value.speed },
  ];
});

function resultClass(result: string): string {
  if (result === "Win") return "tag--ok";
  if (result === "Loss") return "tag--warn";
  return "";
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
                <span
                  v-for="p in replay.players"
                  :key="p.toon_handle"
                  class="tag"
                  :class="resultClass(p.result)"
                >
                  {{ p.name }} · {{ p.play_race }}
                </span>
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

            <p v-if="metadata.replay_summary_conversation" class="muted-copy">
              Summary conversation: <span class="mono-copy">{{ metadata.replay_summary_conversation }}</span>
            </p>
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
            v-for="relation in players"
            :key="relation.replay_player.toon_handle"
            class="list-row player-row"
          >
            <div class="player-row__head">
              <div>
                <strong class="player-row__name">{{ relation.replay_player.name }}</strong>
                <p class="player-row__toon mono-copy">{{ relation.replay_player.toon_handle }}</p>
              </div>
              <div class="tag-row">
                <span class="tag" :class="resultClass(relation.replay_player.result)">
                  {{ relation.replay_player.result }}
                </span>
                <span class="tag">{{ relation.replay_player.play_race }}</span>
              </div>
            </div>

            <div class="player-row__record">
              <template v-if="relation.player_info">
                <span class="tag tag--ok">Player record found</span>
                <RouterLink
                  :to="`/resources/players?toon_handle=${relation.replay_player.toon_handle}`"
                  class="button button--ghost"
                >
                  View player
                </RouterLink>
              </template>
              <span v-else class="tag tag--warn">No player record</span>
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
  font-family: var(--font-display);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  transition: color 150ms ease;
}

.breadcrumb-link:hover {
  color: var(--accent-strong);
}

.page-title {
  margin: 0;
  font-family: var(--font-display);
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
  gap: 12px;
  padding: 16px 18px;
}

.player-row__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.player-row__name {
  font-family: var(--font-display);
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
</style>
