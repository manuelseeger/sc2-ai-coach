<script setup lang="ts">
import PanelHeading from "./PanelHeading.vue";

withDefaults(
  defineProps<{
    primaryEyebrow?: string;
    primaryTitle: string;
    primaryIntro?: string;
    secondaryEyebrow?: string;
    secondaryTitle?: string;
    secondaryIntro?: string;
  }>(),
  {
    primaryEyebrow: "Filters",
    primaryIntro: undefined,
    secondaryEyebrow: "Advanced search",
    secondaryTitle: undefined,
    secondaryIntro: undefined,
  },
);
</script>

<template>
  <section class="resource-inbox-controls">
    <article class="panel panel-stack inbox-pane inbox-pane--filter">
      <PanelHeading :eyebrow="primaryEyebrow" :title="primaryTitle" />
      <p v-if="primaryIntro" class="panel-intro inbox-pane__intro">{{ primaryIntro }}</p>
      <slot name="primary" />
    </article>

    <article v-if="$slots.secondary && secondaryTitle" class="panel panel-stack inbox-pane">
      <PanelHeading :eyebrow="secondaryEyebrow" :title="secondaryTitle" />
      <p v-if="secondaryIntro" class="panel-intro inbox-pane__intro">{{ secondaryIntro }}</p>
      <slot name="secondary" />
    </article>
  </section>
</template>