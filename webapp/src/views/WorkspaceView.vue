<script setup lang="ts">
import { adminAreas, resourceRegistry } from "../route-registry";
</script>

<template>
  <section class="stack">
    <header class="hero panel">
      <p class="kicker">Bootstrap slice</p>
      <h2>Admin routes are now source-controlled and explicit.</h2>
      <p>
        This scaffold establishes the workspace, fixed route registry, and typed API client shell
        for the later browser workflows in issue 57.
      </p>
    </header>

    <section class="grid">
      <article class="panel">
        <h3>Workspace areas</h3>
        <ul>
          <li v-for="area in adminAreas.slice(0, 2)" :key="area.id">
            <strong>{{ area.label }}</strong>
            <span>{{ area.description }}</span>
          </li>
        </ul>
      </article>

      <article class="panel">
        <h3>Registry-backed resources</h3>
        <ul>
          <li v-for="resource in resourceRegistry" :key="resource.name">
            <strong>{{ resource.label }}</strong>
            <span>
              {{ resource.description }}
              {{ resource.writable ? "Writable" : "Read-only" }}.
            </span>
          </li>
        </ul>
      </article>
    </section>
  </section>
</template>

<style scoped>
.stack {
  display: grid;
  gap: 24px;
}

.hero h2 {
  margin: 8px 0 12px;
  font-size: clamp(2rem, 4vw, 3.4rem);
  line-height: 0.95;
}

.hero p:last-child {
  max-width: 56ch;
  line-height: 1.7;
}

.kicker {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: #8f5f2a;
  font-size: 0.8rem;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.panel {
  padding: 24px;
  border-radius: 24px;
  background: rgba(255, 252, 246, 0.86);
  border: 1px solid rgba(28, 40, 50, 0.12);
  box-shadow: 0 12px 30px rgba(28, 40, 50, 0.08);
}

ul {
  display: grid;
  gap: 12px;
  padding: 0;
  list-style: none;
}

li {
  display: grid;
  gap: 4px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(28, 40, 50, 0.08);
}

li:last-child {
  border-bottom: none;
}

span {
  color: #58666f;
  line-height: 1.5;
}

@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>