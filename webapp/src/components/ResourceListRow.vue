<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";

const props = withDefaults(
  defineProps<{
    to: string;
    title: string;
    summary?: string | null;
    maxTitleLength?: number;
    ariaLabel?: string;
  }>(),
  {
    summary: null,
    maxTitleLength: 100,
    ariaLabel: undefined,
  },
);

const displayTitle = computed(() => {
  if (props.title.length <= props.maxTitleLength) {
    return props.title;
  }

  return `${props.title.slice(0, Math.max(0, props.maxTitleLength - 1)).trimEnd()}…`;
});
</script>

<template>
  <li class="list-row list-row--linked resource-list-row">
    <RouterLink :to="to" class="list-row__overlay" :aria-label="ariaLabel ?? displayTitle" />

    <div class="resource-list-row__body">
      <div class="split-topline resource-list-row__header">
        <div class="resource-list-row__copy">
          <strong>{{ displayTitle }}</strong>
          <p v-if="summary" class="resource-list-row__summary">{{ summary }}</p>
        </div>
        <div v-if="$slots.aside" class="resource-list-row__aside">
          <slot name="aside" />
        </div>
      </div>

      <div v-if="$slots.meta" class="tag-row resource-list-row__meta">
        <slot name="meta" />
      </div>

      <slot />
    </div>
  </li>
</template>