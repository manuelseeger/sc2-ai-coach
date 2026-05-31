<script setup lang="ts">
import KeyValueGrid from "./KeyValueGrid.vue";
import PanelHeading from "./PanelHeading.vue";

import type { KeyValueItem } from "./KeyValueGrid.vue";

defineProps<{
  eyebrow: string;
  title: string;
  items: KeyValueItem[];
}>();
</script>

<template>
  <article class="panel panel-stack">
    <PanelHeading :eyebrow="eyebrow" :title="title">
      <template v-if="$slots.aside" #aside>
        <slot name="aside" />
      </template>
    </PanelHeading>

    <KeyValueGrid :items="items" />

    <slot />
  </article>
</template>