<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from "vue-router";

import { adminAreas } from "./route-registry";

const route = useRoute();
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div>
        <p class="eyebrow">SC2 AI Coach</p>
        <h1>Admin Workspace</h1>
        <p class="summary">
          Fixed admin routes over the documented API surface. No runtime discovery, no direct
          database browsing.
        </p>
      </div>

      <nav class="nav">
        <RouterLink
          v-for="area in adminAreas"
          :key="area.id"
          :to="area.path"
          class="nav-link"
          :class="{ active: route.path === area.path }"
        >
          <span>{{ area.label }}</span>
          <small>{{ area.description }}</small>
        </RouterLink>
      </nav>
    </aside>

    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
:global(body) {
  margin: 0;
  font-family: "Segoe UI", "Helvetica Neue", sans-serif;
  background:
    radial-gradient(circle at top, rgba(230, 244, 255, 0.9), transparent 38%),
    linear-gradient(180deg, #f6f1e8 0%, #ebe4d7 100%);
  color: #1c2832;
}

:global(*) {
  box-sizing: border-box;
}

:global(a) {
  color: inherit;
  text-decoration: none;
}

.shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
}

.sidebar {
  padding: 32px 24px;
  border-right: 1px solid rgba(28, 40, 50, 0.14);
  background: rgba(252, 248, 240, 0.82);
  backdrop-filter: blur(10px);
}

.eyebrow {
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.76rem;
  color: #8f5f2a;
}

h1 {
  margin: 0;
  font-size: 2.25rem;
  line-height: 1;
}

.summary {
  margin: 14px 0 0;
  line-height: 1.6;
  color: #495761;
}

.nav {
  display: grid;
  gap: 12px;
  margin-top: 32px;
}

.nav-link {
  display: grid;
  gap: 4px;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid transparent;
  transition: transform 180ms ease, border-color 180ms ease, background 180ms ease;
}

.nav-link:hover,
.nav-link.active {
  transform: translateX(4px);
  border-color: rgba(143, 95, 42, 0.32);
  background: rgba(255, 252, 246, 0.96);
}

.nav-link small {
  color: #62717a;
  line-height: 1.4;
}

.content {
  padding: 32px;
}

@media (max-width: 900px) {
  .shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    border-right: none;
    border-bottom: 1px solid rgba(28, 40, 50, 0.14);
  }
}
</style>