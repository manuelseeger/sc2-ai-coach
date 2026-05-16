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
  <section class="panel">
    <p class="kicker">Health</p>
    <h2>Backend readiness</h2>

    <p v-if="loading">Loading backend health...</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>

    <dl v-else-if="health">
      <div>
        <dt>Status</dt>
        <dd>{{ health.status }}</dd>
      </div>
      <div>
        <dt>Database</dt>
        <dd>{{ health.database }}</dd>
      </div>
      <div>
        <dt>DB name</dt>
        <dd>{{ health.db_name }}</dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.panel {
  padding: 24px;
  border-radius: 24px;
  background: rgba(255, 252, 246, 0.86);
  border: 1px solid rgba(28, 40, 50, 0.12);
  box-shadow: 0 12px 30px rgba(28, 40, 50, 0.08);
}

.kicker {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: #8f5f2a;
  font-size: 0.8rem;
}

h2 {
  margin: 8px 0 24px;
}

dl {
  display: grid;
  gap: 16px;
}

div {
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.74);
}

dt {
  color: #62717a;
  font-size: 0.84rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

dd {
  margin: 6px 0 0;
  font-size: 1.25rem;
}
</style>