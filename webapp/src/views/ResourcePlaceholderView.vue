<script setup lang="ts">
import type { ResourceDefinition } from "../types";

defineProps<{
  resource: ResourceDefinition;
}>();
</script>

<template>
  <section class="panel">
    <p class="kicker">Registry-backed route</p>
    <h2>{{ resource.label }}</h2>
    <p>{{ resource.description }}</p>
    <p class="state">
      {{ resource.writable ? "Writable resource flow arrives in a later slice." : "Read-only resource flow arrives in a later slice." }}
    </p>
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
  margin: 8px 0 12px;
}

p {
  line-height: 1.6;
}

.state {
  color: #62717a;
}
</style>