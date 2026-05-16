<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import PanelHeading from "../components/PanelHeading.vue";
import {
  deleteReplayRecord,
  patchReplayRecord,
  replaceReplayRecord,
} from "../replays";
import type { ReplayRecord } from "../types";

const apiClient = createApiClient();
const route = useRoute();
const router = useRouter();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const feedbackMessage = ref<string | null>(null);
const record = ref<ReplayRecord | null>(null);
const patchText = ref("{}");
const replaceText = ref("{}");
const deleting = ref(false);

const replayId = computed(() => String(route.params.replayId ?? ""));

const replayItems = computed(() => {
  if (!record.value) {
    return [];
  }

  return [
    { label: "Replay ID", value: record.value.id, valueClass: "kv-grid__mono" },
    { label: "Map", value: record.value.map_name },
    { label: "Filename", value: record.value.filename },
    { label: "Date", value: new Date(record.value.date).toLocaleString() },
    { label: "Region", value: record.value.region },
    { label: "Type", value: record.value.real_type },
  ];
});

const currentJson = computed(() => JSON.stringify(record.value, null, 2));

function resetEditors(value: ReplayRecord): void {
  patchText.value = JSON.stringify({ filename: value.filename }, null, 2);
  replaceText.value = JSON.stringify(value, null, 2);
}

async function loadRecord(id: string): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  feedbackMessage.value = null;

  try {
    const loaded = await apiClient.getResource<ReplayRecord>("replays", id);
    record.value = loaded;
    resetEditors(loaded);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Unable to load replay detail.";
    record.value = null;
  } finally {
    loading.value = false;
  }
}

async function applyPatch(): Promise<void> {
  if (!record.value) {
    return;
  }

  errorMessage.value = null;
  feedbackMessage.value = null;

  try {
    const patched = await patchReplayRecord(apiClient, record.value.id, JSON.parse(patchText.value));
    record.value = patched;
    resetEditors(patched);
    feedbackMessage.value = "Replay patch saved and reloaded.";
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Replay patch failed.";
  }
}

async function applyReplace(): Promise<void> {
  if (!record.value) {
    return;
  }

  errorMessage.value = null;
  feedbackMessage.value = null;

  try {
    const replaced = await replaceReplayRecord(apiClient, record.value.id, JSON.parse(replaceText.value));
    record.value = replaced;
    resetEditors(replaced);
    feedbackMessage.value = "Replay replacement saved and reloaded.";
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Replay replace failed.";
  }
}

async function removeRecord(): Promise<void> {
  if (!record.value) {
    return;
  }

  deleting.value = true;
  errorMessage.value = null;
  feedbackMessage.value = null;

  try {
    await deleteReplayRecord(apiClient, record.value.id);
    await router.push("/resources/replays");
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Replay delete failed.";
  } finally {
    deleting.value = false;
  }
}

watch(
  replayId,
  async (value) => {
    await loadRecord(value);
  },
  { immediate: true },
);
</script>

<template>
  <section class="page replay-resource-detail-page">
    <header class="panel page-hero">
      <div>
        <p class="eyebrow">Replay document</p>
        <h2 class="page-hero__title">Patch, replace, or delete one replay record</h2>
        <p class="panel-intro">
          This JSON-first maintenance view is the fallback editor for writable replay documents.
        </p>
      </div>

      <div class="button-row">
        <RouterLink to="/resources/replays" class="button button--ghost">Back to replay maintenance</RouterLink>
        <RouterLink v-if="record" :to="`/replays/${record.id}`" class="button button--accent">
          Open curated replay view
        </RouterLink>
      </div>
    </header>

    <p v-if="loading" class="muted-copy">Loading replay document...</p>
    <p v-else-if="errorMessage && !record" class="feedback error-copy">{{ errorMessage }}</p>

    <template v-else-if="record">
      <section class="detail-grid">
        <article class="panel panel-stack">
          <PanelHeading eyebrow="Current replay" :title="record.map_name">
            <template #aside>
              <span class="pill">{{ record.filename }}</span>
            </template>
          </PanelHeading>

          <KeyValueGrid :items="replayItems" />

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
            <button type="button" class="button button--accent" @click="applyReplace">
              Replace document
            </button>
            <button type="button" class="button button--danger" :disabled="deleting" @click="removeRecord">
              {{ deleting ? "Deleting..." : "Delete replay" }}
            </button>
          </div>
        </article>
      </section>
    </template>
  </section>
</template>