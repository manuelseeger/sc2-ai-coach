<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { ApiError, createApiClient } from "../api";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PanelHeading from "../components/PanelHeading.vue";
import PageHeader from "../components/PageHeader.vue";
import { formatDate } from "../formatters";
import { loadPlayerDetail } from "../players";
import type { PaginatedResponse, PlayerAliasRecord, PlayerInfoRecord, PlayerPortraitMetadataRecord, ReplayRecord } from "../types";

const apiClient = createApiClient();
const route = useRoute();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const player = ref<PlayerInfoRecord | null>(null);
const aliases = ref<PlayerAliasRecord[]>([]);
const portraitMetadata = ref<PlayerPortraitMetadataRecord | null>(null);
const replays = ref<PaginatedResponse<ReplayRecord> | null>(null);

const toonHandle = computed(() => String(route.params.toonHandle ?? ""));

const playerItems = computed(() => {
  if (!player.value) return [];

  return [
    { label: "Toon handle", value: player.value.toon_handle, valueClass: "kv-grid__mono" },
    { label: "Name", value: player.value.name },
    { label: "Aliases", value: String(aliases.value.length) },
    { label: "Tags", value: player.value.tags?.join(", ") || "None" },
  ];
});

function portraitsForAlias(index: number) {
  return portraitMetadata.value?.aliases[index]?.portraits ?? [];
}

watch(
  toonHandle,
  async (value) => {
    loading.value = true;
    errorMessage.value = null;

    try {
      const detail = await loadPlayerDetail(apiClient, value);
      player.value = detail.player;
      aliases.value = detail.aliases;
      portraitMetadata.value = detail.portraitMetadata;
      replays.value = detail.replays;
    } catch (error) {
      errorMessage.value = error instanceof ApiError ? error.message : "Unable to load player review.";
      player.value = null;
      aliases.value = [];
      portraitMetadata.value = null;
      replays.value = null;
    } finally {
      loading.value = false;
    }
  },
  { immediate: true },
);
</script>

<template>
  <section class="page player-detail-page">
    <PageHeader
      :title="player ? player.name : 'Player detail'"
      breadcrumb-label="← Players"
      breadcrumb-to="/players"
    >
      <template #actions>
        <RouterLink v-if="player" :to="`/resources/players/${player.toon_handle}`" class="button button--ghost">
          Maintenance
        </RouterLink>
      </template>
    </PageHeader>

    <LoadingErrorEmpty :loading="loading" :error="errorMessage" loading-message="Loading player detail...">
      <template v-if="player && portraitMetadata && replays">
      <section class="detail-grid">
        <article class="panel panel-stack">
          <PanelHeading eyebrow="Player overview" title="Metrics">
            <template #aside>
              <span class="pill">{{ aliases.length }} aliases</span>
            </template>
          </PanelHeading>

          <KeyValueGrid class="list-block-spacing" :items="playerItems" />
        </article>

        <article class="panel panel-stack">
          <PanelHeading eyebrow="Portraits" title="Player Portraits" />

          <div class="portrait-grid">
            <div class="portrait-card">
              <strong>Primary portrait</strong>
              <img
                v-if="portraitMetadata.portrait.available"
                :src="portraitMetadata.portrait.url"
                :alt="`${player.name} primary portrait`"
                class="portrait-card__image"
              />
              <p v-else class="muted-copy">No primary portrait stored.</p>
            </div>

            <div class="portrait-card">
              <strong>Constructed portrait</strong>
              <img
                v-if="portraitMetadata.portrait_constructed.available"
                :src="portraitMetadata.portrait_constructed.url"
                :alt="`${player.name} constructed portrait`"
                class="portrait-card__image"
              />
              <p v-else class="muted-copy">No constructed portrait stored.</p>
            </div>
          </div>
        </article>
      </section>

      <article class="panel panel-stack">
        <PanelHeading eyebrow="Aliases" title="Names & Portraits" />

        <ul class="list list-block-spacing">
          <li v-for="(alias, index) in aliases" :key="`${alias.name}-${index}`" class="list-row alias-row">
            <div class="split-topline">
              <div>
                <strong>{{ alias.name }}</strong>
                <p class="muted-copy">Seen on {{ alias.seen_on ? formatDate(alias.seen_on) : "Unknown" }}</p>
              </div>
              <span class="tag">{{ portraitsForAlias(index).length }} portraits</span>
            </div>

            <div v-if="portraitsForAlias(index).length" class="alias-portrait-row">
              <img
                v-for="portrait in portraitsForAlias(index)"
                :key="portrait.url"
                :src="portrait.url"
                :alt="`${alias.name} portrait ${portrait.index + 1}`"
                class="alias-portrait-row__image"
              />
            </div>
            <p v-else class="muted-copy">No alias portrait media stored for this name.</p>
          </li>
        </ul>
      </article>

      <article class="panel panel-stack">
        <PanelHeading eyebrow="Related replays" title="Recent Replays">
          <template #aside>
            <span class="pill">{{ replays.docs_quantity }} replays</span>
          </template>
        </PanelHeading>

        <p v-if="replays.docs.length === 0" class="muted-copy">No related replays found for this player.</p>

        <ul v-else class="list list-block-spacing">
          <li v-for="replay in replays.docs" :key="replay.id" class="list-row list-row--linked">
            <RouterLink :to="`/replays/${replay.id}`" class="list-row__overlay" aria-label="Open replay" />
            <div class="split-topline">
              <strong>{{ replay.map_name }}</strong>
              <span class="tag">{{ formatDate(replay.date) }}</span>
            </div>

            <div class="tag-row">
              <span class="tag">{{ replay.real_type }}</span>
              <span class="tag">{{ replay.players.length }} players</span>
            </div>
          </li>
        </ul>
      </article>
      </template>
    </LoadingErrorEmpty>
  </section>
</template>

<style scoped>
.portrait-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.portrait-card {
  display: grid;
  gap: 12px;
}

.portrait-card__image,
.alias-portrait-row__image {
  display: block;
  width: 100%;
  max-width: 140px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(16, 24, 38, 0.9), rgba(10, 16, 26, 1));
}

.alias-row {
  display: grid;
  gap: 12px;
}

.alias-portrait-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
</style>