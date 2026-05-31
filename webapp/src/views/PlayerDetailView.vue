<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { ApiError, createApiClient } from "../api";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PanelHeading from "../components/PanelHeading.vue";
import PageHeader from "../components/PageHeader.vue";
import { formatDate, sc2pulseUrl } from "../formatters";
import { loadPlayerDetail, patchPlayerRecord } from "../players";
import type { PaginatedResponse, PlayerAliasRecord, PlayerInfoRecord, PlayerPortraitMetadataRecord, ReplayRecord } from "../types";

const apiClient = createApiClient();
const route = useRoute();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const player = ref<PlayerInfoRecord | null>(null);
const aliases = ref<PlayerAliasRecord[]>([]);
const portraitMetadata = ref<PlayerPortraitMetadataRecord | null>(null);
const replays = ref<PaginatedResponse<ReplayRecord> | null>(null);

const tags = ref<string[]>([]);
const newTag = ref("");
const savingTags = ref(false);
const tagError = ref<string | null>(null);

const toonHandle = computed(() => String(route.params.toonHandle ?? ""));
const pulseUrl = computed(() => sc2pulseUrl(player.value?.toon_handle));

const playerItems = computed(() => {
  if (!player.value) return [];

  return [
    { label: "Toon handle", value: player.value.toon_handle, valueClass: "kv-grid__mono" },
    { label: "Name", value: player.value.name },
    { label: "Aliases", value: String(aliases.value.length) },
  ];
});

async function saveTags(nextTags: string[]): Promise<void> {
  if (!player.value) return;

  const previous = tags.value;
  savingTags.value = true;
  tagError.value = null;
  tags.value = nextTags;

  try {
    const patched = await patchPlayerRecord(apiClient, player.value.toon_handle, { tags: nextTags });
    player.value = patched;
    tags.value = patched.tags ?? [];
  } catch (error) {
    tags.value = previous;
    tagError.value = error instanceof ApiError ? error.message : "Unable to update tags.";
  } finally {
    savingTags.value = false;
  }
}

function addTag(): void {
  const value = newTag.value.trim();
  if (!value || tags.value.includes(value)) {
    newTag.value = "";
    return;
  }
  newTag.value = "";
  void saveTags([...tags.value, value]);
}

function removeTag(tag: string): void {
  void saveTags(tags.value.filter((existing) => existing !== tag));
}

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
      tags.value = detail.player.tags ?? [];
      tagError.value = null;
      newTag.value = "";
    } catch (error) {
      errorMessage.value = error instanceof ApiError ? error.message : "Unable to load player review.";
      player.value = null;
      aliases.value = [];
      portraitMetadata.value = null;
      replays.value = null;
      tags.value = [];
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
        <a
          v-if="player && pulseUrl"
          :href="pulseUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="button button--ghost"
        >
          sc2pulse ↗
        </a>
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

          <div class="tag-editor list-block-spacing">
            <span class="form-label">Tags</span>
            <div class="tag-row">
              <span v-for="tag in tags" :key="tag" class="tag tag-editor__chip">
                {{ tag }}
                <button
                  type="button"
                  class="tag-editor__remove"
                  :disabled="savingTags"
                  :aria-label="`Remove tag ${tag}`"
                  @click="removeTag(tag)"
                >
                  ×
                </button>
              </span>
              <span v-if="!tags.length" class="muted-copy">No tags yet.</span>
            </div>
            <form class="tag-editor__add" @submit.prevent="addTag">
              <input
                v-model="newTag"
                class="text-input"
                type="text"
                placeholder="Add a tag…"
                :disabled="savingTags"
              />
              <button type="submit" class="button" :disabled="savingTags || !newTag.trim()">Add</button>
            </form>
            <p v-if="tagError" class="muted-copy tag-editor__error">{{ tagError }}</p>
          </div>
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

.tag-editor {
  display: grid;
  gap: 8px;
}

.tag-editor__chip {
  gap: 6px;
  text-transform: none;
}

.tag-editor__remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  background: none;
  color: inherit;
  cursor: pointer;
  font-size: 0.9rem;
  line-height: 1;
  opacity: 0.7;
}

.tag-editor__remove:hover:not(:disabled) {
  opacity: 1;
}

.tag-editor__remove:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.tag-editor__add {
  display: flex;
  gap: 8px;
}

.tag-editor__add .text-input {
  flex: 1;
}

.tag-editor__error {
  color: var(--danger-soft);
}
</style>