<script setup lang="ts">
import JsonPrettyPrint from "./JsonPrettyPrint.vue";
import PanelHeading from "./PanelHeading.vue";

withDefaults(
  defineProps<{
    eyebrow?: string;
    title?: string;
    value: unknown;
    depth?: number;
  }>(),
  {
    eyebrow: "Source",
    title: "Raw JSON",
    depth: 2,
  },
);
</script>

<template>
  <article class="panel panel-stack resource-json-panel">
    <PanelHeading :eyebrow="eyebrow" :title="title" />
    <div class="resource-json-panel__content">
      <JsonPrettyPrint :value="value" :depth="depth" />
    </div>
  </article>
</template>