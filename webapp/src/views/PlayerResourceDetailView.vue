<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import PanelHeading from "../components/PanelHeading.vue";
import { deletePlayerRecord, loadPlayerResourceDetail, patchPlayerRecord, replacePlayerRecord } from "../players";
import type { PlayerInfoRecord } from "../types";

const apiClient = createApiClient();
const route = useRoute();
const router = useRouter();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const feedbackMessage = ref<string | null>(null);
const record = ref<PlayerInfoRecord | null>(null);
const patchText = ref("{}");
const replaceText = ref("{}");
const deleting = ref(false);

const toonHandle = computed(() => String(route.params.toonHandle ?? ""));

const playerItems = computed(() => {
  if (!record.value) return [];

  return [
    { label: "Toon handle", value: record.value.toon_handle, valueClass: "kv-grid__mono" },
    { label: "Name", value: record.value.name },
    { label: "Aliases", value: String(record.value.aliases.length) },
    { label: "Tags", value: record.value.tags?.join(", ") || "None" },
  ];
});

const currentJson = computed(() => JSON.stringify(record.value, null, 2));

function resetEditors(value: PlayerInfoRecord): void {
  patchText.value = JSON.stringify(
    {
      name: value.name,
      aliases: value.aliases,
      tags: value.tags,
    },
    null,
    2,
  );
  replaceText.value = JSON.stringify(value, null, 2);
}

async function loadRecord(id: string): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  feedbackMessage.value = null;

  try {
    const loaded = await loadPlayerResourceDetail(apiClient, id);
    record.value = loaded;
    resetEditors(loaded);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Unable to load player detail.";
    record.value = null;
  } finally {
    loading.value = false;
  }
}

async function applyPatch(): Promise<void> {
  if (!record.value) return;

  errorMessage.value = null;
  feedbackMessage.value = null;

  try {
    const patched = await patchPlayerRecord(apiClient, record.value.toon_handle, JSON.parse(patchText.value));
    record.value = patched;
    resetEditors(patched);
    feedbackMessage.value = "Patch saved to MongoDB and reloaded.";
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Patch request failed.";
  }
}

async function applyReplace(): Promise<void> {
  if (!record.value) return;

  errorMessage.value = null;
  feedbackMessage.value = null;

  try {
    const replaced = await replacePlayerRecord(apiClient, record.value.toon_handle, JSON.parse(replaceText.value));
    record.value = replaced;
    resetEditors(replaced);
    feedbackMessage.value = "Replace saved to MongoDB and reloaded.";
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Replace request failed.";
  }
}

async function removeRecord(): Promise<void> {
  if (!record.value) return;

  deleting.value = true;
  errorMessage.value = null;
  feedbackMessage.value = null;

  try {
    await deletePlayerRecord(apiClient, record.value.toon_handle);
    await router.push("/resources/players");
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Delete request failed.";
  } finally {
    deleting.value = false;
  }
}

watch(toonHandle, async (value) => {
  await loadRecord(value);
}, { immediate: true });
</script>

<template>
  <section class="page player-detail-page">
    <header class="panel page-hero">
      <div>
        <p class="eyebrow">Player detail</p>
        <h2 class="page-hero__title">Inspect and edit one persisted player document</h2>
        <p class="panel-intro">
          This maintenance view stays document-centric while the curated player review keeps
          portraits, aliases, and replay navigation front and center.
        </p>
      </div>

      <div class="button-row">
        <RouterLink to="/resources/players" class="button button--ghost">Back to inbox</RouterLink>
        <RouterLink :to="`/players/${toonHandle}`" class="button button--ghost">Open player review</RouterLink>
      </div>
    </header>

    <p v-if="loading" class="muted-copy">Loading player detail...</p>
    <p v-else-if="errorMessage && !record" class="feedback error-copy">{{ errorMessage }}</p>

    <template v-else-if="record">
      <section class="detail-grid">
        <article class="panel panel-stack">
          <PanelHeading eyebrow="Current record" :title="record.name">
            <template #aside>
              <span class="tag">{{ record.aliases.length }} aliases</span>
            </template>
          </PanelHeading>

          <KeyValueGrid :items="playerItems" />

          <label class="form-field form-field--wide">
            <span class="form-label">Current JSON</span>
            <textarea class="text-area" :value="currentJson" readonly />
          </label>
        </article>

        <article class="panel panel-stack">
          <PanelHeading eyebrow="Write actions" title="Patch, replace, or delete" />

          <p v-if="feedbackMessage" class="feedback">{{ feedbackMessage }}</p>
          <p v-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>

          <label class="form-field form-field--wide">
            <span class="form-label">Patch JSON</span>
            <textarea v-model="patchText" class="text-area" spellcheck="false" />
          </label>

          <div class="button-row">
            <button type="button" class="button" @click="applyPatch">Apply patch</button>
          </div>

          <label class="form-field form-field--wide">
            <span class="form-label">Replace JSON</span>
            <textarea v-model="replaceText" class="text-area" spellcheck="false" />
          </label>

          <div class="button-row">
            <button type="button" class="button button--accent" @click="applyReplace">Replace document</button>
            <button type="button" class="button button--danger" :disabled="deleting" @click="removeRecord">
              {{ deleting ? "Deleting..." : "Delete player" }}
            </button>
          </div>
        </article>
      </section>
    </template>
  </section>
</template>