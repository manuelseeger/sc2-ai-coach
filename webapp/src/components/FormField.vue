<script setup lang="ts">
defineProps<{
  label: string;
}>();
</script>

<template>
  <label class="form-field">
    <span class="form-label">{{ label }}</span>
    <slot />
  </label>
</template>