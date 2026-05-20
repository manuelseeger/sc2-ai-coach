<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { ApiError, createApiClient } from "../api";
import DetailMetadataPanel from "../components/DetailMetadataPanel.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PageHeader from "../components/PageHeader.vue";
import ResourceJsonPanel from "../components/ResourceJsonPanel.vue";
import {
  loadReadOnlyResourceDetail,
  type ReadOnlyResourceName,
  type ReadOnlyResourceRecord,
} from "../read-only-resources";
import { formatDate, formatUsd } from "../formatters";
import type {
  ConversationItemRecord,
  ResourceDefinition,
  ResponseRecord,
  SessionRecord,
} from "../types";

const props = defineProps<{
  resource: ResourceDefinition;
}>();

const apiClient = createApiClient();
const route = useRoute();

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const record = ref<ReadOnlyResourceRecord | null>(null);

const resourceName = computed(() => props.resource.name as ReadOnlyResourceName);
const recordId = computed(() => String(route.params.recordId ?? ""));
const headerIntro = computed(() =>
  resourceName.value === "sessions"
    ? "View the stored session record and open the curated session screen for linked context."
    : "View the details of this record. Open the conversation for full context.",
);

function toConversationItem(value: ReadOnlyResourceRecord): ConversationItemRecord {
  return value as ConversationItemRecord;
}

function toResponseRecord(value: ReadOnlyResourceRecord): ResponseRecord {
  return value as ResponseRecord;
}

function toSessionRecord(value: ReadOnlyResourceRecord): SessionRecord {
  return value as SessionRecord;
}

const title = computed(() => {
  if (!record.value) {
    return props.resource.label;
  }

  if (resourceName.value === "sessions") {
    const session = toSessionRecord(record.value);
    return formatDate(session.session_date, session.id);
  }

  if (resourceName.value === "responses") {
    const response = toResponseRecord(record.value);
    return response.response_id ?? response.id;
  }

  const item = toConversationItem(record.value);
  return item.name ?? item.type;
});

const detailItems = computed(() => {
  if (!record.value) {
    return [];
  }

  if (resourceName.value === "sessions") {
    const session = toSessionRecord(record.value);
    return [
      { label: "Record ID", value: session.id, valueClass: "kv-grid__mono" },
      { label: "Session date", value: formatDate(session.session_date) },
      { label: "AI backend", value: session.ai_backend },
      { label: "Conversations", value: session.conversations.length },
      {
        label: "Current conversation",
        value: session.current_conversation ?? "None",
        valueClass: session.current_conversation ? "kv-grid__mono" : undefined,
      },
      {
        label: "Twitch conversation",
        value: session.twitch_conversation ?? "None",
        valueClass: session.twitch_conversation ? "kv-grid__mono" : undefined,
      },
      { label: "Total tokens", value: session.total_tokens },
      { label: "Total cost", value: formatUsd(session.total_cost) },
    ];
  }

  if (resourceName.value === "responses") {
    const response = toResponseRecord(record.value);
    return [
      { label: "Record ID", value: response.id, valueClass: "kv-grid__mono" },
      { label: "Conversation", value: response.conversation, valueClass: "kv-grid__mono" },
      { label: "Response ID", value: response.response_id ?? "None", valueClass: "kv-grid__mono" },
      { label: "Model", value: response.model ?? "Unknown" },
      { label: "Status", value: response.status ?? "Unknown" },
      { label: "Total tokens", value: response.total_tokens },
      { label: "Total cost", value: formatUsd(response.total_cost) },
      { label: "Streamed", value: response.streamed ? "Yes" : "No" },
    ];
  }

  const item = toConversationItem(record.value);
  return [
    { label: "Record ID", value: item.id, valueClass: "kv-grid__mono" },
    { label: "Conversation", value: item.conversation, valueClass: "kv-grid__mono" },
    { label: "Type", value: item.type },
    { label: "Role", value: item.role ?? "None" },
    { label: "Order", value: item.order },
    { label: "Response ID", value: item.response_id ?? "None", valueClass: "kv-grid__mono" },
    { label: "Source", value: item.source ?? "None" },
  ];
});

const curatedResourcePath = computed(() => {
  if (!record.value) {
    return props.resource.name === "sessions" ? "/sessions" : "/conversations";
  }

  if (resourceName.value === "sessions") {
    return `/sessions/${record.value.id}`;
  }

  return `/conversations/${(record.value as ConversationItemRecord | ResponseRecord).conversation}`;
});

const curatedActionLabel = computed(() =>
  resourceName.value === "sessions" ? "Open session" : "Open conversation",
);

async function loadRecord(id: string): Promise<void> {
  loading.value = true;
  errorMessage.value = null;

  try {
    record.value = await loadReadOnlyResourceDetail(apiClient, resourceName.value, id);
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : `Unable to load ${props.resource.label.toLowerCase()} detail.`;
    record.value = null;
  } finally {
    loading.value = false;
  }
}

watch(recordId, async (value) => {
  await loadRecord(value);
}, { immediate: true });
</script>

<template>
  <section class="page read-only-resource-detail-page">
    <PageHeader
      variant="hero"
      eyebrow="Inspection"
      :title="title"
      :intro="headerIntro"
    >
      <template #actions>
        <RouterLink :to="`/resources/${resource.name}`" class="button button--ghost">Back to inbox</RouterLink>
        <RouterLink v-if="record" :to="curatedResourcePath" class="button button--accent">
          {{ curatedActionLabel }}
        </RouterLink>
      </template>
    </PageHeader>

    <LoadingErrorEmpty :loading="loading" :error="errorMessage && !record ? errorMessage : null" loading-message="Loading...">
      <template v-if="record">
        <section class="resource-detail-layout">
          <DetailMetadataPanel eyebrow="Details" title="Record details" :items="detailItems">
            <template #aside>
              <span class="pill pill--amber">Read only</span>
            </template>
          </DetailMetadataPanel>

          <ResourceJsonPanel :value="record" title="Record JSON" />
        </section>
      </template>
    </LoadingErrorEmpty>
  </section>
</template>
