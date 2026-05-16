<script setup lang="ts">
withDefaults(
  defineProps<{
    eyebrow: string;
    title: string;
    level?: "h2" | "h3";
  }>(),
  {
    level: "h3",
  },
);
</script>

<template>
  <div class="section-heading">
    <div>
      <p class="eyebrow">{{ eyebrow }}</p>
      <component :is="level" class="panel-heading__title">{{ title }}</component>
    </div>

    <slot name="aside" />
  </div>
</template>

<style scoped>
.panel-heading__title {
  margin: 6px 0 0;
  font-family: var(--font-display);
  font-size: clamp(1.8rem, 3vw, 2.8rem);
  line-height: 0.94;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
</style>