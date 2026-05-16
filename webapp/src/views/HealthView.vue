<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiError, createApiClient } from "../api";
import KeyValueGrid from "../components/KeyValueGrid.vue";
import PanelHeading from "../components/PanelHeading.vue";
import type { HealthResponse } from "../types";

const client = createApiClient();
const health = ref<HealthResponse | null>(null);
const errorMessage = ref<string | null>(null);
const loading = ref(true);

const healthItems = computed(() => {
  if (!health.value) {
    return [];
  }

  return [
    { label: "Status", value: health.value.status },
    { label: "Database", value: health.value.database },
    { label: "DB name", value: health.value.db_name },
  ];
});

onMounted(async () => {
  try {
    health.value = await client.getHealth();
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Health request failed.";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="page">
    <article class="panel panel-stack">
      <PanelHeading eyebrow="Health" title="Backend readiness" level="h2">
        <template #aside>
          <span class="pill" :class="health ? 'pill--accent' : 'pill--amber'">
            {{ loading ? "Polling" : health ? "Reachable" : "Attention" }}
          </span>
        </template>
      </PanelHeading>

      <p class="panel-intro">
        Lightweight operator check for the backend process and its configured database target.
      </p>

      <p v-if="loading" class="list-row feedback">Loading backend health...</p>
      <p v-else-if="errorMessage" class="list-row feedback error-copy">{{ errorMessage }}</p>

      <KeyValueGrid v-else-if="health" :items="healthItems" />
    </article>
  </section>
</template>