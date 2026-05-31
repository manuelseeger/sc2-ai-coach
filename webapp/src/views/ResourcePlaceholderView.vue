<script setup lang="ts">
import { computed } from "vue";

import KeyValueGrid from "../components/KeyValueGrid.vue";
import PanelHeading from "../components/PanelHeading.vue";
import type { ResourceDefinition } from "../types";

const props = defineProps<{
  resource: ResourceDefinition;
}>();

const resourceItems = computed(() => [
  { label: "Route family", value: `/api/${props.resource.name}`, valueClass: "kv-grid__mono" },
  {
    label: "Default stance",
    value: props.resource.writable ? "Operator maintenance" : "Inspection only",
  },
  { label: "Current slice", value: "Scaffold placeholder" },
]);
</script>

<template>
  <section class="page">
    <article class="panel panel-stack">
      <PanelHeading eyebrow="Registry-backed route" :title="resource.label" level="h2">
        <template v-if="!resource.writable" #aside>
          <span class="pill pill--amber">Read only</span>
        </template>
      </PanelHeading>

      <p class="panel-intro">{{ resource.description }}</p>

      <KeyValueGrid :items="resourceItems" />

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
.state-block {
  margin-top: 4px;
}
</style>