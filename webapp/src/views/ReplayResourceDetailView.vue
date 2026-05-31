<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import CrudPanel from "../components/CrudPanel.vue";
import DetailMetadataPanel from "../components/DetailMetadataPanel.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PageHeader from "../components/PageHeader.vue";
import ResourceJsonPanel from "../components/ResourceJsonPanel.vue";
import { formatDate } from "../formatters";
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
    { label: "Date", value: formatDate(record.value.date) },
    { label: "Region", value: record.value.region },
    { label: "Type", value: record.value.real_type },
  ];
});

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
    <PageHeader
      variant="hero"
      eyebrow="Replay"
      title="Edit or delete this replay"
      intro="Edit replay fields or remove this entry entirely."
    >
      <template #actions>
        <RouterLink to="/resources/replays" class="button button--ghost">Back to replays</RouterLink>
        <RouterLink v-if="record" :to="`/replays/${record.id}`" class="button button--accent">
          Open replay
        </RouterLink>
      </template>
    </PageHeader>

    <LoadingErrorEmpty :loading="loading" :error="errorMessage && !record ? errorMessage : null" loading-message="Loading...">
      <template v-if="record">
        <section class="resource-detail-layout">
          <section class="detail-grid">
            <DetailMetadataPanel eyebrow="Current replay" :title="record.map_name" :items="replayItems">
              <template #aside>
                <span class="pill">{{ record.filename }}</span>
              </template>
            </DetailMetadataPanel>

            <CrudPanel
              :feedback-message="feedbackMessage"
              :error-message="errorMessage"
              :patch-text="patchText"
              :replace-text="replaceText"
              :deleting="deleting"
              delete-button-label="Delete replay"
              @patch="applyPatch"
              @replace="applyReplace"
              @delete="removeRecord"
              @update:patch-text="patchText = $event"
              @update:replace-text="replaceText = $event"
            />
          </section>

          <ResourceJsonPanel :value="record" title="Replay JSON" />
        </section>
      </template>
    </LoadingErrorEmpty>
  </section>
</template>