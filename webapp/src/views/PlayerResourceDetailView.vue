<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import CrudPanel from "../components/CrudPanel.vue";
import DetailMetadataPanel from "../components/DetailMetadataPanel.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PageHeader from "../components/PageHeader.vue";
import ResourceJsonPanel from "../components/ResourceJsonPanel.vue";
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
    feedbackMessage.value = "Changes saved.";
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Update failed.";
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
    feedbackMessage.value = "Changes saved.";
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Update failed.";
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
    <PageHeader
      variant="hero"
      eyebrow="Player"
      title="Edit player details"
      intro="Edit player fields or remove this player entry entirely."
    >
      <template #actions>
        <RouterLink to="/resources/players" class="button button--ghost">Back to inbox</RouterLink>
        <RouterLink :to="`/players/${toonHandle}`" class="button button--ghost">Open player</RouterLink>
      </template>
    </PageHeader>

    <LoadingErrorEmpty :loading="loading" :error="errorMessage && !record ? errorMessage : null" loading-message="Loading player detail...">
      <template v-if="record">
        <section class="resource-detail-layout">
          <section class="detail-grid">
            <DetailMetadataPanel eyebrow="Current record" :title="record.name" :items="playerItems">
              <template #aside>
                <span class="tag">{{ record.aliases.length }} aliases</span>
              </template>
            </DetailMetadataPanel>

            <CrudPanel
              :feedback-message="feedbackMessage"
              :error-message="errorMessage"
              :patch-text="patchText"
              :replace-text="replaceText"
              :deleting="deleting"
              delete-button-label="Delete player"
              @patch="applyPatch"
              @replace="applyReplace"
              @delete="removeRecord"
              @update:patch-text="patchText = $event"
              @update:replace-text="replaceText = $event"
            />
          </section>

          <ResourceJsonPanel :value="record" title="Player JSON" />
        </section>
      </template>
    </LoadingErrorEmpty>
  </section>
</template>