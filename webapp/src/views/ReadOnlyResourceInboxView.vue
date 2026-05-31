<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { ApiError, createApiClient } from "../api";
import FormField from "../components/FormField.vue";
import LoadingErrorEmpty from "../components/LoadingErrorEmpty.vue";
import PageHeader from "../components/PageHeader.vue";
import PanelHeading from "../components/PanelHeading.vue";
import ResourceInboxControls from "../components/ResourceInboxControls.vue";
import ResourceListRow from "../components/ResourceListRow.vue";
import { formatCount, formatDate, formatUsd } from "../formatters";
import {
  loadReadOnlyResourceInbox,
  lookupResponseRecord,
  queryReadOnlyResourceRecords,
  type ReadOnlyResourceName,
  type ReadOnlyResourceRecord,
} from "../read-only-resources";
import type {
  ConversationItemRecord,
  QueryBody,
  ResourceDefinition,
  ResponseRecord,
  PaginatedResponse,
  SessionRecord,
} from "../types";

const props = defineProps<{
  resource: ResourceDefinition;
}>();

const apiClient = createApiClient();
const router = useRouter();

const loading = ref(true);
const queryLoading = ref(false);
const errorMessage = ref<string | null>(null);
const lookupErrorMessage = ref<string | null>(null);
const inbox = ref<PaginatedResponse<ReadOnlyResourceRecord> | null>(null);
const queryResults = ref<PaginatedResponse<ReadOnlyResourceRecord> | null>(null);
const responseLookupId = ref("");

const resourceName = computed(() => props.resource.name as ReadOnlyResourceName);
const isResponseResource = computed(() => resourceName.value === "responses");
const isSessionResource = computed(() => resourceName.value === "sessions");
const queryText = ref(
  JSON.stringify(
    {
      filter: {},
      sort: { [isSessionResource.value ? "session_date" : "created_at"]: -1 },
      current_page: 1,
      docs_per_page: 10,
    },
    null,
    2,
  ),
);
const listTitle = computed(() =>
  props.resource.name === "responses"
    ? "Response records"
    : props.resource.name === "sessions"
      ? "Session records"
      : "Conversation items",
);
const headerIntro = computed(() =>
  isSessionResource.value
    ? "Browse stored session records and open the curated session view for context."
    : "Browse stored records and open the full conversation view for context.",
);

function toConversationItem(record: ReadOnlyResourceRecord): ConversationItemRecord {
  return record as ConversationItemRecord;
}

function toResponseRecord(record: ReadOnlyResourceRecord): ResponseRecord {
  return record as ResponseRecord;
}

function toSessionRecord(record: ReadOnlyResourceRecord): SessionRecord {
  return record as SessionRecord;
}

function recordTitle(record: ReadOnlyResourceRecord): string {
  if (isSessionResource.value) {
    const session = toSessionRecord(record);
    return formatDate(session.session_date, session.id);
  }

  if (isResponseResource.value) {
    const response = toResponseRecord(record);
    return response.response_id ?? response.id;
  }

  const item = toConversationItem(record);
  if (item.type === "message") {
    return item.role ? `${item.role} message` : "message";
  }
  return item.name ?? item.type;
}

function recordSummary(record: ReadOnlyResourceRecord): string {
  if (isSessionResource.value) {
    const session = toSessionRecord(record);
    return `${session.ai_backend} • ${formatCount(session.conversations.length)} conversations • ${formatUsd(session.total_cost)}`;
  }

  if (isResponseResource.value) {
    const response = toResponseRecord(record);
    return `${response.model ?? "Unknown model"} • ${response.status ?? "Unknown status"}`;
  }

  const item = toConversationItem(record);
  if (item.type === "message") {
    return item.content.map((part) => part.text).join(" ").slice(0, 120) || "Message content";
  }
  if (item.output) {
    return item.output.slice(0, 120);
  }
  return item.response_id ?? "Transcript record";
}

function detailPath(record: ReadOnlyResourceRecord): string {
  return `/resources/${props.resource.name}/${record.id}`;
}

function recordTimestamp(record: ReadOnlyResourceRecord): string {
  if (isSessionResource.value) {
    return formatDate(toSessionRecord(record).session_date);
  }

  return formatDate((record as ConversationItemRecord | ResponseRecord).created_at);
}

async function loadInbox(): Promise<void> {
  loading.value = true;
  errorMessage.value = null;

  try {
    inbox.value = await loadReadOnlyResourceInbox(apiClient, resourceName.value, {
      sort: isSessionResource.value ? "-session_date" : "-created_at",
      current_page: 1,
      docs_per_page: 25,
    });
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : `Unable to load ${props.resource.label.toLowerCase()}.`;
    inbox.value = null;
  } finally {
    loading.value = false;
  }
}

async function runQuery(): Promise<void> {
  queryLoading.value = true;
  errorMessage.value = null;

  try {
    const body = JSON.parse(queryText.value) as QueryBody;
    queryResults.value = await queryReadOnlyResourceRecords(apiClient, resourceName.value, body);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Query request failed.";
  } finally {
    queryLoading.value = false;
  }
}

async function openResponseLookup(): Promise<void> {
  lookupErrorMessage.value = null;

  try {
    const record = await lookupResponseRecord(apiClient, responseLookupId.value);
    await router.push(`/resources/responses/${record.id}`);
  } catch (error) {
    lookupErrorMessage.value = error instanceof ApiError ? error.message : "Lookup failed.";
  }
}

onMounted(async () => {
  await loadInbox();
});
</script>

<template>
  <section class="page read-only-resource-page">
    <PageHeader
      eyebrow="Inspection"
      :title="resource.label"
      :intro="headerIntro"
    >
      <template #actions>
        <span class="pill pill--amber">Read only</span>
      </template>
    </PageHeader>

    <ResourceInboxControls
      primary-eyebrow="Query"
      primary-title="Inspect records"
      primary-intro="Run a JSON query to inspect a narrower slice of stored records. Rows below open the raw detail view."
    >
      <template #primary>
        <FormField class="form-field--wide" label="Filter">
          <textarea v-model="queryText" class="text-area" spellcheck="false" />
        </FormField>

        <div class="button-row">
          <button type="button" class="button" :disabled="queryLoading" @click="runQuery">
            {{ queryLoading ? "Running..." : "Run query" }}
          </button>
        </div>

        <div v-if="isResponseResource" class="lookup-block">
          <FormField class="form-field--wide" label="Look up by response ID">
            <input
              v-model="responseLookupId"
              class="text-input"
              type="text"
              placeholder="resp-..."
            />
          </FormField>
          <div class="button-row">
            <button type="button" class="button button--ghost" @click="openResponseLookup">
              Open response
            </button>
          </div>
          <p v-if="lookupErrorMessage" class="feedback error-copy">{{ lookupErrorMessage }}</p>
        </div>

        <p v-if="errorMessage && inbox" class="feedback error-copy">{{ errorMessage }}</p>
      </template>
    </ResourceInboxControls>

    <section class="resource-detail-layout">
      <article class="panel panel-stack">
        <PanelHeading eyebrow="Recent records" :title="listTitle">
          <template #aside>
            <span v-if="inbox" class="tag">{{ inbox.docs_quantity }} records</span>
          </template>
        </PanelHeading>

        <LoadingErrorEmpty :loading="loading" :error="errorMessage && !inbox ? errorMessage : null" :empty="!inbox || inbox.docs.length === 0" loading-message="Loading..." empty-message="No records to show.">
          <ul class="list">
            <ResourceListRow
              v-for="record in inbox.docs"
              :key="record.id"
              :to="detailPath(record)"
              :title="recordTitle(record)"
              :summary="recordSummary(record)"
              :aria-label="`Open ${resource.label} record ${record.id}`"
            >
              <template #meta>
                <span class="tag mono-copy">{{ record.id }}</span>
                <span class="tag mono-copy">{{ recordTimestamp(record) }}</span>
              </template>
            </ResourceListRow>
          </ul>
        </LoadingErrorEmpty>
      </article>

      <article class="panel panel-stack">
        <PanelHeading eyebrow="Query results" title="Filtered records">
          <template #aside>
            <span v-if="queryResults" class="tag">{{ queryResults.docs_quantity }} matches</span>
          </template>
        </PanelHeading>

        <p v-if="!queryResults" class="muted-copy">Results will appear here after running a filter.</p>
        <p v-else-if="queryResults.docs.length === 0" class="muted-copy">No results found.</p>

        <ul v-else class="list">
          <ResourceListRow
            v-for="record in queryResults.docs"
            :key="`query-${record.id}`"
            :to="detailPath(record)"
            :title="recordTitle(record)"
            :summary="recordSummary(record)"
            :aria-label="`Open filtered ${resource.label} record ${record.id}`"
          >
            <template #meta>
              <span class="tag mono-copy">{{ record.id }}</span>
              <span class="tag mono-copy">{{ recordTimestamp(record) }}</span>
            </template>
          </ResourceListRow>
        </ul>
      </article>
    </section>
  </section>
</template>

<style scoped>
.lookup-block {
  display: grid;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border-muted);
}

.text-input {
  width: 100%;
  min-height: 44px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-strong);
  background: rgba(8, 12, 20, 0.92);
  color: var(--text);
}
</style>