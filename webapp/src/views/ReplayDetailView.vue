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
  if (!replay.value) {
    return [];
  }

  return [
    { label: "Replay ID", value: replay.value.id, valueClass: "kv-grid__mono" },
    { label: "Date", value: new Date(replay.value.date).toLocaleString() },
    { label: "Map", value: replay.value.map_name },
    { label: "Filename", value: replay.value.filename },
    { label: "Region", value: replay.value.region },
    { label: "Length", value: `${Math.round(replay.value.real_length / 60)} min` },
    { label: "Type", value: replay.value.real_type },
    { label: "Speed", value: replay.value.speed },
  ];
});

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
      errorMessage.value = error instanceof ApiError ? error.message : "Unable to load replay detail.";
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
    <header class="panel page-hero">
      <div>
        <p class="eyebrow">Replay detail</p>
        <h2 class="page-hero__title">Replay facts, metadata, and player records together</h2>
        <p class="panel-intro">
          This curated screen stays focused on operator inspection while the generic replay
          maintenance path remains a separate expert workflow.
        </p>
      </div>

      <div class="button-row">
        <RouterLink to="/replays" class="button button--ghost">Back to replay inbox</RouterLink>
        <RouterLink v-if="replay" :to="`/resources/replays/${replay.id}`" class="button button--accent">
          Open replay maintenance
        </RouterLink>
      </div>
    </header>

    <p v-if="loading" class="muted-copy">Loading replay detail...</p>
    <p v-else-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>

    <template v-else-if="replay">
      <section class="detail-grid">
        <article class="panel panel-stack">
          <PanelHeading eyebrow="Replay facts" :title="replay.map_name">
            <template #aside>
              <span class="pill">{{ replay.players.length }} players</span>
            </template>
          </PanelHeading>

          <KeyValueGrid :items="replayItems" />

          <div class="tag-row">
            <span v-for="playerRecord in replay.players" :key="playerRecord.toon_handle" class="tag">
              {{ playerRecord.name }} · {{ playerRecord.play_race }} · {{ playerRecord.result }}
            </span>
          </div>
        </article>

        <article class="panel panel-stack">
          <PanelHeading eyebrow="Replay metadata" title="Replay-scoped annotation">
            <template #aside>
              <span class="pill pill--amber">Relationship route</span>
            </template>
          </PanelHeading>

          <template v-if="metadata">
            <p>{{ metadata.description || "No description recorded." }}</p>
            <div class="tag-row">
              <span v-for="tag in metadata.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>
            <p class="muted-copy">
              Summary conversation: {{ metadata.replay_summary_conversation || "None" }}
            </p>
          </template>

          <p v-else class="muted-copy">
            No replay metadata exists yet for this replay. Use replay maintenance if you need to
            create or repair the underlying documents.
          </p>
        </article>
      </section>

      <article class="panel panel-stack">
        <PanelHeading eyebrow="Player records" title="Participating players and known identities">
          <template #aside>
            <span class="pill">GET /api/replays/{{ replay.id }}/players</span>
          </template>
        </PanelHeading>

        <ul class="list list-block-spacing">
          <li v-for="relation in players" :key="relation.replay_player.toon_handle" class="list-row">
            <div class="split-topline">
              <div>
                <strong>{{ relation.replay_player.name }}</strong>
                <p class="mono-copy">{{ relation.replay_player.toon_handle }}</p>
              </div>
              <span class="tag">{{ relation.replay_player.play_race }} · {{ relation.replay_player.result }}</span>
            </div>

            <p v-if="relation.player_info">
              Known player record: {{ relation.player_info.name }}
            </p>
            <p v-else class="muted-copy">No persisted player record was found for this replay participant.</p>

            <RouterLink
              :to="{ path: '/resources/players', query: { toon_handle: relation.replay_player.toon_handle } }"
              class="list-link"
            >
              Open player records
            </RouterLink>
          </li>
        </ul>
      </article>
    </template>
  </section>
</template>