<script setup lang="ts">
import KeyValueGrid from "./KeyValueGrid.vue";
import PanelHeading from "./PanelHeading.vue";
import FormField from "./FormField.vue";

import type { KeyValueItem } from "./KeyValueGrid.vue";

defineProps<{
  eyebrow: string;
  title: string;
  items: KeyValueItem[];
  jsonText: string;
  jsonLabel?: string;
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

    <FormField class="form-field--wide" :label="jsonLabel ?? 'Current data'">
      <textarea class="text-area" :value="jsonText" readonly />
    </FormField>
  </article>
</template>