<script setup lang="ts">
import { computed } from "vue";

import { renderMessage } from "../message-rendering";
import type { ConversationContentPartRecord } from "../types";
import JsonPrettyPrint from "./JsonPrettyPrint.vue";
import MarkdownRenderer from "./MarkdownRenderer.vue";

const props = defineProps<{
  content: ConversationContentPartRecord[];
}>();

const blocks = computed(() => {
  const text = props.content
    .map((part) => part.text)
    .filter(Boolean)
    .join("\n\n");
  return renderMessage(text);
});
</script>

<template>
  <div class="message-content">
    <template v-for="(block, i) in blocks" :key="i">
      <MarkdownRenderer v-if="block.kind === 'html'" :html="block.html" />
      <div v-else class="message-content__json-block">
        <JsonPrettyPrint :value="block.value" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.message-content {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.message-content__json-block {
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: rgba(7, 10, 16, 0.9);
  border: 1px solid var(--border-muted);
  overflow-x: auto;
}
</style>
