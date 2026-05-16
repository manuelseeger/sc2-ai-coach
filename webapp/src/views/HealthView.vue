<script setup lang="ts">
import { onMounted, ref } from "vue";

import { ApiError, createApiClient } from "../api";
import type { HealthResponse } from "../types";

const client = createApiClient();
const health = ref<HealthResponse | null>(null);
const errorMessage = ref<string | null>(null);
const loading = ref(true);

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
    <article class="panel health-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Health</p>
          <h2>Backend readiness</h2>
        </div>
        <span class="pill" :class="health ? 'pill--accent' : 'pill--amber'">
          {{ loading ? "Polling" : health ? "Reachable" : "Attention" }}
        </span>
      </div>

      <p class="panel-intro">
        Lightweight operator check for the backend process and its configured database target.
      </p>

      <p v-if="loading" class="list-row feedback">Loading backend health...</p>
      <p v-else-if="errorMessage" class="list-row feedback error-copy">{{ errorMessage }}</p>

      <dl v-else-if="health" class="data-grid">
        <div class="data-card">
          <dt>Status</dt>
          <dd>{{ health.status }}</dd>
        </div>
        <div class="data-card">
          <dt>Database</dt>
          <dd>{{ health.database }}</dd>
        </div>
        <div class="data-card">
          <dt>DB name</dt>
          <dd>{{ health.db_name }}</dd>
        </div>
      </dl>
    </article>
  </section>
</template>

<style scoped>
.health-panel {
  display: grid;
  gap: 18px;
}

h2 {
  margin: 6px 0 0;
  font-family: var(--font-display);
  font-size: clamp(1.8rem, 3vw, 2.8rem);
  line-height: 0.94;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.feedback {
  margin: 0;
}

.error-copy {
  color: #ffb0b0;
}
</style>