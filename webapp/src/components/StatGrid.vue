<script setup lang="ts">
import StatTile from "./StatTile.vue";

export interface StatGridItem {
  label: string;
  value: string | number;
  valueClass?: string;
}

withDefaults(
  defineProps<{
    items: StatGridItem[];
    inline?: boolean;
    align?: "left" | "right";
  }>(),
  {
    inline: false,
    align: "right",
  },
);
</script>

<template>
  <div class="stat-grid" :class="{ 'stat-grid--inline': inline }">
    <StatTile
      v-for="item in items"
      :key="item.label"
      :label="item.label"
      :value="item.value"
      :value-class="item.valueClass"
      :align="align"
    />
  </div>
</template>