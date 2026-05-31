<script setup lang="ts">
import { computed } from "vue";

import { prepareDisplay } from "../json-display";
import type { ConversationItemRecord, ToolDefinition } from "../types";
import JsonPrettyPrint from "./JsonPrettyPrint.vue";

const props = defineProps<{
  item: ConversationItemRecord;
  toolDef?: ToolDefinition;
}>();

interface FieldRow {
  key: string;
  type: string;
  value: unknown;
  isUnknownType: boolean;
}

function getSchemaProperties(
  toolDef: ToolDefinition | undefined,
): Record<string, Record<string, unknown>> | null {
  if (!toolDef) return null;
  const params = toolDef.parameters;
  if (
    params &&
    typeof params === "object" &&
    "properties" in params &&
    params.properties &&
    typeof params.properties === "object"
  ) {
    return params.properties as Record<string, Record<string, unknown>>;
  }
  return null;
}

function getPrimaryType(schema: Record<string, unknown>): string {
  if (typeof schema.type === "string") return schema.type;

  // anyOf: pick the first non-null type
  if (Array.isArray(schema.anyOf)) {
    for (const entry of schema.anyOf as unknown[]) {
      if (entry && typeof entry === "object") {
        const t = (entry as Record<string, unknown>).type;
        if (typeof t === "string" && t !== "null") return t;
      }
    }
  }

  return "unknown";
}

const toolName = computed(() => props.item.name ?? "unknown tool");

const fields = computed<FieldRow[]>(() => {
  const args = props.item.arguments ?? {};
  const properties = getSchemaProperties(props.toolDef);

  if (properties) {
    return Object.entries(properties).map(([key, schema]) => ({
      key,
      type: getPrimaryType(schema),
      value: key in args ? args[key] : undefined,
      isUnknownType: false,
    }));
  }

  // Fallback: key order + unknown badge
  return Object.entries(args).map(([key, value]) => ({
    key,
    type: "unknown",
    value,
    isUnknownType: true,
  }));
});

function isNullValue(value: unknown): boolean {
  return value === null;
}

function isJsonValue(value: unknown): boolean {
  return prepareDisplay(value).isJson;
}
</script>

<template>
  <div class="tool-call-card">
    <p class="tool-call-card__name">{{ toolName }}</p>
    <dl v-if="fields.length > 0" class="tool-call-card__grid">
      <div v-for="field in fields" :key="field.key" class="tool-call-card__field">
        <dt class="tool-call-card__label">
          {{ field.key }}
        </dt>
        <div class="tool-call-card__type">
          <span class="type-badge" :class="{ 'type-badge--unknown': field.isUnknownType }">
            {{ field.type }}
          </span>
        </div>
        <dd class="tool-call-card__value">
          <span v-if="field.value === undefined" class="value--absent" />
          <code v-else-if="isNullValue(field.value)" class="value--null">null</code>
          <JsonPrettyPrint v-else-if="isJsonValue(field.value)" :value="field.value" />
          <span v-else class="value--text">{{ String(field.value) }}</span>
        </dd>
      </div>
    </dl>
    <p v-else class="tool-call-card__empty">No arguments</p>
  </div>
</template>

<style scoped>
.tool-call-card {
  display: grid;
  gap: 10px;
}

.tool-call-card__name {
  font-family: var(--mono, monospace);
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--purple-strong, #c59cff);
  margin: 0;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.tool-call-card__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 8px;
  margin: 0;
}

.tool-call-card__field {
  display: grid;
  grid-template-columns: minmax(88px, 132px) minmax(54px, 72px) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  padding: 10px 12px;
  border-radius: var(--radius-sm, 8px);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.tool-call-card__label {
  display: block;
  font-size: 0.7rem;
  color: var(--text-dim, #aab3c2);
  font-family: var(--display, sans-serif);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.tool-call-card__type {
  display: flex;
  align-items: start;
}

.type-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.62rem;
  min-height: 22px;
  padding: 0 8px;
  border-radius: var(--radius-sm, 3px);
  background: rgba(197, 156, 255, 0.12);
  color: var(--purple-strong, #c59cff);
  font-family: var(--mono, monospace);
  text-transform: lowercase;
  letter-spacing: 0;
  line-height: 1.6;
  justify-self: start;
}

.type-badge--unknown {
  background: transparent;
  border: 1px solid var(--border-muted, #334155);
  color: var(--text-dim, #94a3b8);
}

.tool-call-card__value {
  margin: 0;
  font-size: 0.82rem;
  min-width: 0;
  word-break: break-word;
}

.value--null {
  font-family: var(--mono, monospace);
  color: var(--fg-muted, #94a3b8);
  font-style: italic;
}

.value--text {
  font-family: var(--mono, monospace);
  color: var(--text, #e2e8f0);
}

.tool-call-card__empty {
  font-size: 0.78rem;
  color: var(--text-dim, #94a3b8);
  margin: 0;
}

@media (max-width: 720px) {
  .tool-call-card__field {
    grid-template-columns: minmax(0, 1fr);
    gap: 6px;
  }
}
</style>
