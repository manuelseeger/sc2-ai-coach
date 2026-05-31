<script setup lang="ts">
withDefaults(
  defineProps<{
    loading?: boolean;
    error?: string | null;
    empty?: boolean;
    loadingMessage?: string;
    emptyMessage?: string;
    loadingClass?: string;
    errorClass?: string;
    emptyClass?: string;
  }>(),
  {
    loading: false,
    error: null,
    empty: false,
    loadingMessage: "Loading...",
    emptyMessage: "No results.",
    loadingClass: "muted-copy",
    errorClass: "feedback error-copy",
    emptyClass: "muted-copy",
  },
);
</script>

<template>
  <slot v-if="loading" name="loading">
    <p :class="loadingClass">{{ loadingMessage }}</p>
  </slot>
  <slot v-else-if="error" name="error">
    <p :class="errorClass">{{ error }}</p>
  </slot>
  <slot v-else-if="empty" name="empty">
    <p :class="emptyClass">{{ emptyMessage }}</p>
  </slot>
  <slot v-else />
</template>