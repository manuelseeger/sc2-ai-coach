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