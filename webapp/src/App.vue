<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from "vue-router";

import { adminAreas, resourceRegistry } from "./route-registry";

const route = useRoute();

const primaryNav = adminAreas.filter(
  (area) => !area.path.startsWith("/resources/") && area.id !== "workspace" && area.id !== "health"
);
const healthArea = adminAreas.find((area) => area.id === "health")!;

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
        <RouterLink to="/" class="brand-link">
          <p class="eyebrow">SC2 AI Coach</p>
          <h1 class="brand-title">Admin</h1>
        </RouterLink>
      </div>

      <nav class="nav">
        <RouterLink
          v-for="area in primaryNav"
          :key="area.id"
          :to="area.path"
          class="nav-link"
          :class="{ active: isAreaActive(area.path) }"
        >
          <span>{{ area.label }}</span>
        </RouterLink>

        <div class="nav-divider" />
        <p class="nav-section-label">Resources</p>

        <RouterLink
          v-for="resource in resourceRegistry"
          :key="resource.name"
          :to="`/resources/${resource.name}`"
          class="nav-link nav-link--resource"
          :class="{ active: isAreaActive(`/resources/${resource.name}`) }"
        >
          <span>{{ resource.label }}</span>
          <small v-if="!resource.writable" class="nav-link__badge">read only</small>
        </RouterLink>
      </nav>

      <div class="nav-utility">
        <RouterLink
          :to="healthArea.path"
          class="nav-link nav-link--utility"
          :class="{ active: isAreaActive(healthArea.path) }"
        >
          <span>{{ healthArea.label }}</span>
        </RouterLink>
      </div>
    </aside>

    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style>
.brand-link {
  display: block;
  text-decoration: none;
}

.nav-link--resource {
  padding: 9px 14px 9px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.nav-link--resource span {
  font-size: 0.87rem;
}

.nav-link__badge {
  color: var(--text-muted);
  font-size: 0.65rem;
  font-family: var(--display);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
</style>
