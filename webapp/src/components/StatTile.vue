<script setup lang="ts">
defineProps<{
  label: string;
  value: string | number;
  valueClass?: string;
  align?: "left" | "right";
}>();
</script>

<template>
  <div class="stat-tile" :class="align === 'left' ? 'stat-tile--left' : 'stat-tile--right'">
    <span class="stat-tile__label">{{ label }}</span>
    <span class="stat-tile__value" :class="valueClass">{{ value }}</span>
  </div>
</template>