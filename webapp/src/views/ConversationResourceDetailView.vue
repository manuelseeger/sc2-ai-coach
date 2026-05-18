<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import PanelHeading from "../components/PanelHeading.vue";
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
    { label: "Created", value: new Date(record.value.created_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short", hour12: false }) },
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
    <header class="panel page-hero">
      <div>
        <p class="eyebrow">Conversation detail</p>
        <h2 class="page-hero__title">Edit conversation details</h2>
        <p class="panel-intro">
          Update or delete this conversation. Messages are managed separately.
        </p>
      </div>

      <div class="button-row">
        <RouterLink to="/resources/conversations" class="button button--ghost">Back to inbox</RouterLink>
        <RouterLink v-if="record" :to="`/conversations/${record.id}`" class="button button--accent">Open conversation</RouterLink>
      </div>
    </header>

    <p v-if="loading" class="muted-copy">Loading conversation detail...</p>
    <p v-else-if="errorMessage && !record" class="feedback error-copy">{{ errorMessage }}</p>

    <template v-else-if="record">
      <section class="detail-grid">
        <article class="panel panel-stack">
          <PanelHeading eyebrow="Current record" :title="`Conversation ${record.id}`">
            <template #aside>
              <span class="tag">{{ record.item_count }} items</span>
            </template>
          </PanelHeading>

          <KeyValueGrid :items="conversationItems" />

          <label class="form-field form-field--wide">
            <span class="form-label">Current data</span>
            <textarea class="text-area" :value="currentJson" readonly />
          </label>
        </article>

        <article class="panel panel-stack">
          <PanelHeading eyebrow="Edit" title="Update or delete" />

          <p v-if="feedbackMessage" class="feedback">{{ feedbackMessage }}</p>
          <p v-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>

          <label class="form-field form-field--wide">
            <span class="form-label">Fields to update</span>
            <textarea v-model="patchText" class="text-area" spellcheck="false" />
          </label>

          <div class="button-row">
            <button type="button" class="button" @click="applyPatch">Save changes</button>
          </div>

          <label class="form-field form-field--wide">
            <span class="form-label">Full record</span>
            <textarea v-model="replaceText" class="text-area" spellcheck="false" />
          </label>

          <div class="button-row">
            <button type="button" class="button button--accent" @click="applyReplace">Replace</button>
            <button type="button" class="button button--danger" :disabled="deleting" @click="removeRecord">
              {{ deleting ? "Deleting..." : "Delete conversation" }}
            </button>
          </div>
        </article>
      </section>
    </template>
  </section>
</template>