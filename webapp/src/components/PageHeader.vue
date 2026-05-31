<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: "breadcrumb" | "hero";
    title: string;
    eyebrow?: string;
    breadcrumbLabel?: string;
    breadcrumbTo?: string;
    intro?: string;
    titleClass?: string;
  }>(),
  {
    variant: "breadcrumb",
    eyebrow: undefined,
    breadcrumbLabel: undefined,
    breadcrumbTo: undefined,
    intro: undefined,
    titleClass: undefined,
  },
);
</script>

<template>
  <header :class="variant === 'hero' ? 'panel page-hero' : 'page-header'">
    <div :class="variant === 'hero' ? 'page-header__copy' : 'page-header__breadcrumb'">
      <RouterLink
        v-if="variant === 'breadcrumb' && breadcrumbLabel && breadcrumbTo"
        :to="breadcrumbTo"
        class="breadcrumb-link"
      >
        {{ breadcrumbLabel }}
      </RouterLink>
      <p v-if="eyebrow" class="eyebrow">{{ eyebrow }}</p>
      <h2 :class="[variant === 'hero' ? 'page-hero__title' : 'page-title', titleClass]">{{ title }}</h2>
      <p v-if="variant === 'hero' && intro" class="panel-intro">{{ intro }}</p>
    </div>

    <div v-if="$slots.actions" class="button-row page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>