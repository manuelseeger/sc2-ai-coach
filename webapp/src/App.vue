<template>
  <div class="app-shell">
    <header class="app-header">
      <RouterLink class="app-brand" to="/">SC2 AI Coach Admin</RouterLink>
      <nav class="app-nav" aria-label="Primary">
        <RouterLink to="/">Workspace</RouterLink>
        <RouterLink to="/sessions">Sessions</RouterLink>
        <RouterLink to="/conversations">Conversations</RouterLink>
        <RouterLink to="/map-stats">Map Stats</RouterLink>
      </nav>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>