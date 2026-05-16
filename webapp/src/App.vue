<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from "vue-router";

import { adminAreas } from "./route-registry";

const route = useRoute();

function isAreaActive(path: string): boolean {
  if (path === "/") {
    return route.path === "/";
  }

  return route.path === path || route.path.startsWith(`${path}/`);
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand-block">
        <p class="eyebrow">SC2 AI Coach</p>
        <h1 class="brand-title">Operator Console</h1>
        <p class="brand-summary">
          Fixed admin routes over the documented API surface. No runtime discovery, no direct
          database browsing.
        </p>

        <div class="status-strip">
          <span class="pill pill--accent">Domain-shaped routes</span>
          <span class="pill pill--amber">Registry-backed CRUD</span>
        </div>
      </div>

      <nav class="nav">
        <RouterLink
          v-for="area in adminAreas"
          :key="area.id"
          :to="area.path"
          class="nav-link"
          :class="{ active: isAreaActive(area.path) }"
        >
          <span>{{ area.label }}</span>
          <small>{{ area.description }}</small>
        </RouterLink>
      </nav>

      <section class="rail-footer">
        <strong>Current stance</strong>
        <p>
          Curated resource workflows stay primary. Generic maintenance remains a fallback surface.
        </p>
      </section>
    </aside>

    <main class="content">
      <RouterView />
    </main>
  </div>
</template>
