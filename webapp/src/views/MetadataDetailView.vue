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
    {
      label: "Summary conversation",
      value: record.value.replay_summary_conversation ?? "None",
      valueClass: record.value.replay_summary_conversation ? "kv-grid__mono" : undefined,
    },
    { label: "Created", value: formatDate(record.value.created_at) },
    { label: "Updated", value: formatDate(record.value.updated_at) },
  ];
});

const metadataTitle = computed(() => {
  const description = record.value?.description?.trim();

  if (!description) {
    return "Untitled metadata";
  }

  if (description.length <= 20) {
    return description;
  }

  return `${description.slice(0, 19).trimEnd()}…`;
});

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
    feedbackMessage.value = "Changes saved.";
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Update failed.";
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
    feedbackMessage.value = "Changes saved.";
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Update failed.";
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
    <PageHeader
      variant="hero"
      eyebrow="Annotation detail"
      title="Edit replay annotation"
      intro="Review and update annotation details, or remove this annotation entirely."
    >
      <template #actions>
        <RouterLink to="/resources/metadata" class="button button--ghost">Back to inbox</RouterLink>
        <RouterLink to="/resources/metadata/new" class="button button--accent">New annotation</RouterLink>
      </template>
    </PageHeader>

    <LoadingErrorEmpty :loading="loading" :error="errorMessage && !record ? errorMessage : null" loading-message="Loading metadata detail...">
      <template v-if="record">
        <section class="resource-detail-layout">
          <section class="detail-grid">
            <DetailMetadataPanel eyebrow="Current record" :title="metadataTitle" :items="metadataItems">
              <template #aside>
                <span class="tag">{{ record.tags.length }} tags</span>
              </template>
              <div class="tag-row">
                <span v-for="tag in record.tags" :key="tag" class="tag">{{ tag }}</span>
              </div>
            </DetailMetadataPanel>

            <CrudPanel
              :feedback-message="feedbackMessage"
              :error-message="errorMessage"
              :patch-text="patchText"
              :replace-text="replaceText"
              :deleting="deleting"
              delete-button-label="Delete annotation"
              @patch="applyPatch"
              @replace="applyReplace"
              @delete="removeRecord"
              @update:patch-text="patchText = $event"
              @update:replace-text="replaceText = $event"
            />
          </section>

          <ResourceJsonPanel :value="record" title="Annotation JSON" />
        </section>
      </template>
    </LoadingErrorEmpty>
  </section>
</template>