<script setup lang="ts">
export interface KeyValueItem {
  label: string;
  value: string | number;
  valueClass?: string;
}

defineProps<{
  items: KeyValueItem[];
}>();
</script>

<template>
  <dl class="data-grid">
    <div v-for="item in items" :key="item.label" class="data-card">
      <dt>{{ item.label }}</dt>
      <dd :class="item.valueClass">{{ item.value }}</dd>
    </div>
  </dl>
</template>

<style scoped>
.kv-grid__mono {
  font-size: 1rem;
  font-family: var(--font-mono);
  overflow-wrap: anywhere;
}
</style>