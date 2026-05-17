<script setup lang="ts">
import { RouterLink } from "vue-router";
import { resourceRegistry } from "../route-registry";

const quickLinks = [
  {
    label: "Sessions",
    description: "Recent coaching sessions with linked conversations",
    path: "/sessions",
    eyebrow: "Read only",
    accent: "accent",
  },
  {
    label: "Conversations",
    description: "Transcript-focused conversation review with typed filters",
    path: "/conversations",
    eyebrow: "Curated review",
    accent: "accent",
  },
  {
    label: "Replays",
    description: "Replay inbox with metadata and player relationships",
    path: "/replays",
    eyebrow: "Curated review",
    accent: "accent",
  },
  {
    label: "Map Stats",
    description: "Aggregated matchup win-rate data by map",
    path: "/map-stats",
    eyebrow: "Read only",
    accent: "muted",
  },
  {
    label: "Health",
    description: "Backend and database readiness",
    path: "/health",
    eyebrow: "System",
    accent: "muted",
  },
];
</script>

<template>
  <section class="page workspace-page">
    <header class="workspace-hero panel">
      <div class="workspace-hero__copy">
        <p class="eyebrow">SC2 AI Coach</p>
        <h2 class="workspace-hero__title">Admin Workspace</h2>
        <p class="workspace-hero__lead">
          Inspect and manage coaching sessions, replays, players, and conversations. All data is
          served from the standalone API backed by MongoDB.
        </p>
      </div>
    </header>

    <section class="workspace-section">
      <p class="workspace-section__label">Quick access</p>
      <div class="workspace-quicklinks">
        <RouterLink
          v-for="link in quickLinks"
          :key="link.path"
          :to="link.path"
          class="quicklink-card"
          :class="`quicklink-card--${link.accent}`"
        >
          <p class="quicklink-card__eyebrow">{{ link.eyebrow }}</p>
          <strong class="quicklink-card__label">{{ link.label }}</strong>
          <p class="quicklink-card__desc">{{ link.description }}</p>
          <span class="quicklink-card__arrow">→</span>
        </RouterLink>
      </div>
    </section>

    <section class="workspace-section">
      <p class="workspace-section__label">Resource families</p>
      <div class="resource-table">
        <RouterLink
          v-for="resource in resourceRegistry"
          :key="resource.name"
          :to="`/resources/${resource.name}`"
          class="resource-row"
        >
          <span class="resource-row__name">{{ resource.label }}</span>
          <span class="resource-row__desc">{{ resource.description }}</span>
          <span class="tag" :class="resource.writable ? 'tag--ok' : 'tag--warn'">
            {{ resource.writable ? "Writable" : "Read only" }}
          </span>
          <span class="resource-row__path">/{{ resource.name }}</span>
        </RouterLink>
      </div>
    </section>
  </section>
</template>

<style scoped>
.workspace-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 32px;
  min-height: 160px;
  background:
    radial-gradient(ellipse at 80% 50%, rgba(86, 194, 255, 0.07), transparent 60%),
    radial-gradient(ellipse at 20% 80%, rgba(167, 139, 250, 0.04), transparent 50%),
    linear-gradient(180deg, rgba(15, 22, 34, 0.96), rgba(9, 14, 22, 0.99)),
    var(--panel-stripe);
}

.workspace-hero__copy {
  max-width: 60ch;
}

.workspace-hero__title {
  margin: 8px 0 14px;
  font-family: var(--display);
  font-size: clamp(2rem, 3.5vw, 3rem);
  line-height: 0.92;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.workspace-hero__lead {
  margin: 0;
  color: var(--text-dim);
  line-height: 1.65;
  max-width: 56ch;
}

.workspace-section {
  display: grid;
  gap: 12px;
}

.workspace-section__label {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.7rem;
  font-family: var(--display);
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.workspace-quicklinks {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}

.quicklink-card {
  display: grid;
  gap: 8px;
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background:
    linear-gradient(180deg, rgba(15, 22, 34, 0.94), rgba(9, 14, 22, 0.99)),
    var(--panel-stripe);
  transition: border-color 180ms ease, background 180ms ease, transform 150ms ease;
  cursor: pointer;
}

.quicklink-card:hover {
  border-color: var(--border-strong);
  background:
    radial-gradient(ellipse at top right, rgba(86, 194, 255, 0.06), transparent 50%),
    linear-gradient(180deg, rgba(18, 27, 42, 0.97), rgba(10, 16, 26, 1)),
    var(--panel-stripe);
  transform: translateY(-2px);
}

.quicklink-card--accent {
  border-color: rgba(86, 194, 255, 0.2);
}

.quicklink-card__eyebrow {
  margin: 0;
  color: var(--accent);
  font-size: 0.68rem;
  font-family: var(--display);
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.quicklink-card__label {
  font-family: var(--display);
  font-size: 1.25rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text);
}

.quicklink-card__desc {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.88rem;
  line-height: 1.5;
}

.quicklink-card__arrow {
  margin-top: 4px;
  color: var(--accent-strong);
  font-size: 1.1rem;
  opacity: 0;
  transition: opacity 150ms ease, transform 150ms ease;
}

.quicklink-card:hover .quicklink-card__arrow {
  opacity: 1;
  transform: translateX(4px);
}

.resource-table {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.resource-row {
  display: grid;
  grid-template-columns: 160px 1fr auto 140px;
  align-items: center;
  gap: 20px;
  padding: 14px 18px;
  border-bottom: 1px solid rgba(114, 154, 204, 0.08);
  background: linear-gradient(180deg, rgba(11, 17, 27, 0.74), rgba(8, 13, 22, 0.9));
  transition: background 140ms ease;
}

.resource-row:last-child {
  border-bottom: none;
}

.resource-row:hover {
  background:
    linear-gradient(180deg, rgba(16, 24, 38, 0.92), rgba(10, 16, 28, 0.97)),
    var(--panel-stripe);
}

.resource-row__name {
  font-family: var(--display);
  font-size: 0.92rem;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text);
}

.resource-row__desc {
  color: var(--text-dim);
  font-size: 0.9rem;
}

.resource-row__path {
  color: var(--text-muted);
  font-family: var(--mono);
  font-size: 0.78rem;
  text-align: right;
}

@media (max-width: 1100px) {
  .workspace-quicklinks {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .workspace-quicklinks {
    grid-template-columns: 1fr;
  }

  .resource-row {
    grid-template-columns: 1fr auto;
    grid-template-rows: auto auto;
  }

  .resource-row__desc {
    grid-column: 1 / -1;
  }

  .resource-row__path {
    display: none;
  }
}
</style>
