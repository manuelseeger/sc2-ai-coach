<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import CrudPanel from "../components/CrudPanel.vue";
import DetailMetadataPanel from "../components/DetailMetadataPanel.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PageHeader from "../components/PageHeader.vue";
import { formatDate } from "../formatters";
import {
  deleteConversationRecord,
  loadConversationDetail,
  patchConversationRecord,
  replaceConversationRecord,
} from "../conversations";
import type { ConversationRecord } from "../types";

const apiClient = createApiClient();
const route = useRoute();
const router = useRouter();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const feedbackMessage = ref<string | null>(null);
const record = ref<ConversationRecord | null>(null);
const patchText = ref("{}");
const replaceText = ref("{}");
const deleting = ref(false);

const conversationId = computed(() => String(route.params.conversationId ?? ""));

const conversationItems = computed(() => {
  if (!record.value) {
    return [];
  }

  return [
    { label: "Conversation ID", value: record.value.id, valueClass: "kv-grid__mono" },
    { label: "Session", value: record.value.session ?? "None", valueClass: record.value.session ? "kv-grid__mono" : undefined },
    { label: "Trigger", value: record.value.trigger },
    { label: "Status", value: record.value.status },
    { label: "Created", value: formatDate(record.value.created_at) },
    { label: "Items", value: record.value.item_count },
  ];
});

const currentJson = computed(() => JSON.stringify(record.value, null, 2));

function resetEditors(value: ConversationRecord): void {
  patchText.value = JSON.stringify(
    {
      status: value.status,
      metadata: value.metadata,
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
    const loaded = await loadConversationDetail(apiClient, id);
    record.value = loaded.conversation;
    resetEditors(loaded.conversation);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Unable to load conversation detail.";
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
    const patched = await patchConversationRecord(apiClient, record.value.id, JSON.parse(patchText.value));
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
    const replaced = await replaceConversationRecord(apiClient, record.value.id, JSON.parse(replaceText.value));
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
    await deleteConversationRecord(apiClient, record.value.id);
    await router.push("/resources/conversations");
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Delete request failed.";
  } finally {
    deleting.value = false;
  }
}

watch(conversationId, async (value) => {
  await loadRecord(value);
}, { immediate: true });
</script>

<template>
  <section class="page conversation-detail-page">
    <PageHeader
      variant="hero"
      eyebrow="Conversation detail"
      title="Edit conversation details"
      intro="Update or delete this conversation. Messages are managed separately."
    >
      <template #actions>
        <RouterLink to="/resources/conversations" class="button button--ghost">Back to inbox</RouterLink>
        <RouterLink v-if="record" :to="`/conversations/${record.id}`" class="button button--accent">Open conversation</RouterLink>
      </template>
    </PageHeader>

    <LoadingErrorEmpty :loading="loading" :error="errorMessage && !record ? errorMessage : null" loading-message="Loading conversation detail...">
      <template v-if="record">
      <section class="detail-grid">
        <DetailMetadataPanel eyebrow="Current record" :title="`Conversation ${record.id}`" :items="conversationItems" :json-text="currentJson">
          <template #aside>
            <span class="tag">{{ record.item_count }} items</span>
          </template>
        </DetailMetadataPanel>

        <CrudPanel
          :feedback-message="feedbackMessage"
          :error-message="errorMessage"
          :patch-text="patchText"
          :replace-text="replaceText"
          :deleting="deleting"
          delete-button-label="Delete conversation"
          @patch="applyPatch"
          @replace="applyReplace"
          @delete="removeRecord"
          @update:patch-text="patchText = $event"
          @update:replace-text="replaceText = $event"
        />
      </section>
      </template>
    </LoadingErrorEmpty>
  </section>
</template>