<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import PanelHeading from "../components/PanelHeading.vue";
import {
  deleteMetadataRecord,
  loadMetadataDetail,
  patchMetadataRecord,
  replaceMetadataRecord,
} from "../metadata";
import type { MetadataRecord } from "../types";

const apiClient = createApiClient();
const route = useRoute();
const router = useRouter();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const feedbackMessage = ref<string | null>(null);
const record = ref<MetadataRecord | null>(null);
const patchText = ref("{}");
const replaceText = ref("{}");
const deleting = ref(false);

const metadataId = computed(() => String(route.params.metadataId ?? ""));

const metadataItems = computed(() => {
  if (!record.value) {
    return [];
  }

  return [
    { label: "Metadata ID", value: record.value.id, valueClass: "kv-grid__mono" },
    { label: "Replay", value: record.value.replay, valueClass: "kv-grid__mono" },
    { label: "Description", value: record.value.description ?? "None" },
    {
      label: "Summary conversation",
      value: record.value.replay_summary_conversation ?? "None",
      valueClass: record.value.replay_summary_conversation ? "kv-grid__mono" : undefined,
    },
    { label: "Created", value: new Date(record.value.created_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short", hour12: false }) },
    { label: "Updated", value: new Date(record.value.updated_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short", hour12: false }) },
  ];
});

const currentJson = computed(() => JSON.stringify(record.value, null, 2));

function resetEditors(value: MetadataRecord): void {
  patchText.value = JSON.stringify(
    {
      description: value.description,
      tags: value.tags,
      replay_summary_conversation: value.replay_summary_conversation,
    },
    null,
    2,
  );
  replaceText.value = JSON.stringify(
    {
      id: value.id,
      replay: value.replay,
      description: value.description,
      tags: value.tags,
      replay_summary_conversation: value.replay_summary_conversation,
    },
    null,
    2,
  );
}

async function loadRecord(id: string): Promise<void> {
  loading.value = true;
  errorMessage.value = null;
  feedbackMessage.value = null;

  try {
    const loaded = await loadMetadataDetail(apiClient, id);
    record.value = loaded;
    resetEditors(loaded);
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : "Unable to load metadata detail.";
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
    const patched = await patchMetadataRecord(apiClient, record.value.id, JSON.parse(patchText.value));
    record.value = patched;
    resetEditors(patched);
    feedbackMessage.value = "Patch saved to MongoDB and reloaded.";
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Patch request failed.";
  }
}

async function applyReplace(): Promise<void> {
  if (!record.value) {
    return;
  }

  errorMessage.value = null;
  feedbackMessage.value = null;

  try {
    const replaced = await replaceMetadataRecord(
      apiClient,
      record.value.id,
      JSON.parse(replaceText.value),
    );
    record.value = replaced;
    resetEditors(replaced);
    feedbackMessage.value = "Replace saved to MongoDB and reloaded.";
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Replace request failed.";
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
    await deleteMetadataRecord(apiClient, record.value.id);
    await router.push("/resources/metadata");
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Delete request failed.";
  } finally {
    deleting.value = false;
  }
}

watch(metadataId, async (value) => {
  await loadRecord(value);
}, { immediate: true });
</script>

<template>
  <section class="page metadata-detail-page">
    <header class="panel page-hero">
      <div>
        <p class="eyebrow">Metadata detail</p>
        <h2 class="page-hero__title">Inspect and edit one persisted metadata document</h2>
        <p class="panel-intro">
          Detail review stays document-centric while JSON patch and replace calls exercise the full
          writable maintenance path against the same record.
        </p>
      </div>

      <div class="button-row">
        <RouterLink to="/resources/metadata" class="button button--ghost">Back to inbox</RouterLink>
        <RouterLink to="/resources/metadata/new" class="button button--accent">New metadata</RouterLink>
      </div>
    </header>

    <p v-if="loading" class="muted-copy">Loading metadata detail...</p>
    <p v-else-if="errorMessage && !record" class="feedback error-copy">{{ errorMessage }}</p>

    <template v-else-if="record">
      <section class="detail-grid">
        <article class="panel panel-stack">
          <PanelHeading eyebrow="Current record" :title="record.description || 'Untitled metadata'">
            <template #aside>
              <span class="tag">{{ record.tags.length }} tags</span>
            </template>
          </PanelHeading>

          <KeyValueGrid :items="metadataItems" />

          <div class="tag-row">
            <span v-for="tag in record.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>

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
              {{ deleting ? "Deleting..." : "Delete metadata" }}
            </button>
          </div>
        </article>
      </section>
    </template>
  </section>
</template>