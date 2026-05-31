<script setup lang="ts">
defineProps<{
  currentPage: number;
  totalPages: number;
}>();

defineEmits<{
  prev: [];
  next: [];
}>();
</script>

<template>
  <div v-if="totalPages > 1" class="pagination-row">
    <button class="button button--ghost" :disabled="currentPage <= 1" @click="$emit('prev')">
      ← Prev
    </button>
    <span class="pagination-label">{{ currentPage }} / {{ totalPages }}</span>
    <button class="button button--ghost" :disabled="currentPage >= totalPages" @click="$emit('next')">
      Next →
    </button>
  </div>
</template>