<script setup lang="ts">
import { computed } from "vue";

import { prepareDisplay } from "../json-display";
import type { ConversationItemRecord } from "../types";
import JsonPrettyPrint from "./JsonPrettyPrint.vue";

const props = defineProps<{
  item: ConversationItemRecord;
  linkedToolName?: string;
}>();

const display = computed(() => prepareDisplay(props.item.output));
</script>

<template>
  <div class="tool-result-card">
    <p v-if="linkedToolName" class="tool-result-card__linked">
      Linked to <span class="tool-result-card__linked-name">{{ linkedToolName }}</span>
    </p>
    <JsonPrettyPrint v-if="display.isJson" :value="display.parsed" />
    <pre v-else class="tool-result-card__body">{{ display.displayText }}</pre>
  </div>
</template>

<style scoped>
.tool-result-card {
  display: grid;
  gap: 10px;
}

.tool-result-card__linked {
  margin: 0;
  font-size: 0.72rem;
  color: var(--text-dim, #94a3b8);
  font-family: var(--display, sans-serif);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.tool-result-card__linked-name {
  color: var(--green-strong, #86efac);
  font-family: var(--mono, monospace);
  text-transform: none;
  letter-spacing: 0;
}

.tool-result-card__body {
  margin: 0;
  white-space: pre-wrap;
  color: var(--text, #e2e8f0);
  font-family: var(--ui, sans-serif);
  line-height: 1.6;
  word-break: break-word;
  font-size: 0.9rem;
}
</style>
