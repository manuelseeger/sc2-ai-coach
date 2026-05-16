<script setup lang="ts">
import KeyValueGrid from "../components/KeyValueGrid.vue";
import PanelHeading from "../components/PanelHeading.vue";
import { adminAreas, resourceRegistry } from "../route-registry";

const primaryAreas = adminAreas.filter(
  (area) => !resourceRegistry.some((resource) => area.id === resource.name),
);

const workspaceMetricItems = [
  { label: "Admin areas", value: adminAreas.length },
  { label: "Registry resources", value: resourceRegistry.length },
  {
    label: "Write-enabled families",
    value: resourceRegistry.filter((resource) => resource.writable).length,
  },
];
</script>

<template>
  <section class="page workspace-page">
    <header class="panel hero-panel">
      <div class="hero-copy">
        <p class="eyebrow">Admin workspace</p>
        <h2>Operate from stable routes, not from generic collection chrome.</h2>
        <p class="panel-intro">
          This entry screen is an operator map for the backend's documented surfaces. Curated
          review flows stay primary, while generic maintenance remains clearly secondary.
        </p>
      </div>

      <KeyValueGrid class="hero-metrics" :items="workspaceMetricItems" />
    </header>

    <section class="workspace-grid">
      <article class="panel">
        <PanelHeading eyebrow="Primary routes" title="Workspace areas">
          <template #aside>
            <span class="pill">Fixed route table</span>
          </template>
        </PanelHeading>

        <ul class="list workspace-list">
          <li v-for="area in primaryAreas" :key="area.id" class="list-row">
            <strong>{{ area.label }}</strong>
            <p>{{ area.description }}</p>
          </li>
        </ul>
      </article>

      <article class="panel">
        <PanelHeading eyebrow="Resource families" title="Registry-backed maintenance">
          <template #aside>
            <span class="pill pill--amber">CRUD where supported</span>
          </template>
        </PanelHeading>

        <ul class="list workspace-list">
          <li v-for="resource in resourceRegistry" :key="resource.name" class="list-row">
            <div class="list-topline">
              <strong>{{ resource.label }}</strong>
              <span class="tag" :class="resource.writable ? 'tag--ok' : 'tag--warn'">
                {{ resource.writable ? "Writable" : "Read only" }}
              </span>
            </div>
            <p>{{ resource.description }}</p>
            <div class="tag-row">
              <span class="tag">/{{ resource.name }}</span>
              <span class="tag">Explicit API family</span>
            </div>
          </li>
        </ul>
      </article>

      <article class="panel briefing-panel">
        <PanelHeading eyebrow="Design direction" title="What this shell should signal" />

        <div class="tag-row brief-tags">
          <span class="pill pill--accent">Dense desktop-first workflow</span>
          <span class="pill">Relationship-heavy views</span>
          <span class="pill">Read-only surfaces stay obvious</span>
        </div>

        <pre class="code-block">Curated session, replay, player, conversation, and map-stat views remain the primary operator path.
Generic maintenance exists, but it should feel like an expert fallback instead of the main story.</pre>
      </article>
    </section>
  </section>
</template>

<style scoped>
.hero-panel {
  display: grid;
  gap: 24px;
}

.hero-copy {
  max-width: 72ch;
}

.hero-panel h2 {
  margin: 8px 0 12px;
  font-family: var(--font-display);
  font-size: clamp(2.2rem, 4vw, 4rem);
  line-height: 0.9;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.workspace-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.workspace-list {
  margin-top: 18px;
}

.list-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.briefing-panel {
  grid-column: 1 / -1;
}

.brief-tags {
  margin: 18px 0;
}

.hero-metrics {
  align-items: stretch;
}

@media (max-width: 900px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}
</style>