<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { ApiError, createApiClient } from "../api";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import PanelHeading from "../components/PanelHeading.vue";
import {
  loadReadOnlyResourceDetail,
  type ReadOnlyResourceName,
  type ReadOnlyResourceRecord,
} from "../read-only-resources";
import type {
  ConversationItemRecord,
  ResourceDefinition,
  ResponseRecord,
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

function toConversationItem(value: ReadOnlyResourceRecord): ConversationItemRecord {
  return value as ConversationItemRecord;
}

function toResponseRecord(value: ReadOnlyResourceRecord): ResponseRecord {
  return value as ResponseRecord;
}

const title = computed(() => {
  if (!record.value) {
    return props.resource.label;
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

  if (resourceName.value === "responses") {
    const response = toResponseRecord(record.value);
    return [
      { label: "Record ID", value: response.id, valueClass: "kv-grid__mono" },
      { label: "Conversation", value: response.conversation, valueClass: "kv-grid__mono" },
      { label: "Response ID", value: response.response_id ?? "None", valueClass: "kv-grid__mono" },
      { label: "Model", value: response.model ?? "Unknown" },
      { label: "Status", value: response.status ?? "Unknown" },
      { label: "Total tokens", value: response.total_tokens },
      { label: "Total cost", value: `$${response.total_cost.toFixed(4)}` },
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
    { label: "Included", value: item.included_in_context ? "Yes" : "No" },
    { label: "Source", value: item.source ?? "None" },
  ];
});

const currentJson = computed(() => JSON.stringify(record.value, null, 2));
const curatedConversationPath = computed(() =>
  record.value ? `/conversations/${record.value.conversation}` : "/conversations",
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
    <header class="page-header">
      <div class="page-header__copy">
        <p class="eyebrow">Inspection</p>
        <h2 class="page-title">{{ title }}</h2>
        <p class="panel-intro">
          View the details of this record. Open the conversation for full context.
        </p>
      </div>

      <div class="button-row">
        <RouterLink :to="`/resources/${resource.name}`" class="button button--ghost">Back to inbox</RouterLink>
        <RouterLink v-if="record" :to="curatedConversationPath" class="button button--accent">
          Open conversation
        </RouterLink>
      </div>
    </header>

    <p v-if="loading" class="muted-copy">Loading...</p>
    <p v-else-if="errorMessage && !record" class="feedback error-copy">{{ errorMessage }}</p>

    <template v-else-if="record">
      <section class="detail-grid">
        <article class="panel panel-stack">
          <PanelHeading eyebrow="Details" title="Record details">
            <template #aside>
              <span class="pill pill--amber">Read only</span>
            </template>
          </PanelHeading>

          <KeyValueGrid :items="detailItems" />
        </article>

        <article class="panel panel-stack">
          <PanelHeading eyebrow="Raw data" title="Stored data" />

          <label class="form-field form-field--wide">
            <span class="form-label">Current data</span>
            <textarea class="text-area" :value="currentJson" readonly />
          </label>
        </article>
      </section>
    </template>
  </section>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-header__copy {
  display: grid;
  gap: 8px;
  max-width: 72ch;
}

.page-title {
  margin: 0;
  font-family: var(--display);
  font-size: clamp(1.7rem, 3vw, 2.5rem);
  line-height: 0.94;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
</style>