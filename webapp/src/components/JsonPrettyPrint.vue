<script setup lang="ts">
import VueJsonPretty from "vue-json-pretty";
import "vue-json-pretty/lib/styles.css";
import { computed } from "vue";

import { prepareDisplay } from "../json-display";

const props = defineProps<{
  value: unknown;
  depth?: number;
}>();

const display = computed(() => prepareDisplay(props.value));
const expandDepth = computed(() => props.depth ?? 2);
</script>

<template>
  <VueJsonPretty
    v-if="display.isJson"
    :data="display.parsed"
    :deep="expandDepth"
    :show-double-quotes="true"
    :show-length="false"
    class="json-pretty-print"
  />
  <span v-else class="json-pretty-print json-pretty-print--text">{{ display.displayText }}</span>
</template>

<style scoped>
.json-pretty-print {
  display: block;
  width: 100%;
  min-width: 0;
  font-family: var(--mono, monospace);
  font-size: 0.78rem;
  line-height: 1.5;
  background: transparent;
  padding: 0;
  overflow-x: auto;
}

.json-pretty-print--text {
  display: block;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Override vue-json-pretty theme colors to match dark admin UI */
:deep(.vjs-tree) {
  background: transparent;
  color: var(--text, #e2e8f0);
  font-family: var(--mono, monospace);
  font-size: 0.78rem;
  min-width: max-content;
  white-space: pre;
}

:deep(.vjs-key) {
  color: var(--accent, #7dd3fc);
}

:deep(.vjs-value-string) {
  color: #86efac;
  white-space: pre;
  word-break: normal;
}

:deep(.vjs-value-number),
:deep(.vjs-value-boolean) {
  color: #f9a8d4;
  white-space: pre;
  word-break: normal;
}

:deep(.vjs-value-null) {
  color: var(--fg-muted, #94a3b8);
  font-style: italic;
  white-space: pre;
}

:deep(.vjs-tree__brackets) {
  color: var(--fg-muted, #94a3b8);
}

:deep(.vjs-tree__content.has-line) {
  border-left-color: var(--border-muted, #334155);
}
</style>
