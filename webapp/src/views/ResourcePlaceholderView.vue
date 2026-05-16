<script setup lang="ts">
import type { ResourceDefinition } from "../types";

defineProps<{
  resource: ResourceDefinition;
}>();
</script>

<template>
  <section class="page">
    <article class="panel resource-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Registry-backed route</p>
          <h2>{{ resource.label }}</h2>
        </div>
        <span class="pill" :class="resource.writable ? 'pill--accent' : 'pill--amber'">
          {{ resource.writable ? "Write-enabled" : "Read only" }}
        </span>
      </div>

      <p class="panel-intro">{{ resource.description }}</p>

      <div class="data-grid resource-grid">
        <div class="data-card">
          <dt>Route family</dt>
          <dd>/api/{{ resource.name }}</dd>
        </div>
        <div class="data-card">
          <dt>Default stance</dt>
          <dd>{{ resource.writable ? "Operator maintenance" : "Inspection only" }}</dd>
        </div>
        <div class="data-card">
          <dt>Current slice</dt>
          <dd>Scaffold placeholder</dd>
        </div>
      </div>

      <div class="list-row state-block">
        <strong>Implementation note</strong>
        <p>
          {{ resource.writable ? "Create, patch, replace, and delete affordances belong here only when the API exposes them." : "List, detail, and query reads stay available here without generic write actions." }}
        </p>
      </div>
    </article>
  </section>
</template>

<style scoped>
.resource-panel {
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

.resource-grid dd {
  font-size: 1rem;
  font-family: var(--font-mono);
  overflow-wrap: anywhere;
}

.state-block {
  margin-top: 4px;
}
</style>