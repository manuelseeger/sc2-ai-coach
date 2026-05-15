<template>
  <section class="workspace-shell">
    <header class="workspace-header">
      <div>
        <p class="eyebrow">Admin Workspace</p>
        <h1>Resource discovery drives the operator surface.</h1>
      </div>
      <p class="workspace-copy">
        The standalone API is the source of truth for which resources are available.
      </p>
    </header>

    <p v-if="loading" class="workspace-copy">Loading workspace resources…</p>
    <p v-else-if="error" class="workspace-error">{{ error }}</p>

    <section v-else class="resource-grid">
      <article v-for="resource in resources" :key="resource.name" class="resource-card">
        <header>
          <h2>{{ resource.title }}</h2>
          <span>{{ resource.available ? 'Available' : 'Unavailable' }}</span>
        </header>
        <p class="resource-path">{{ resource.path }}</p>
        <p class="resource-collection">Collection: {{ resource.collection ?? 'n/a' }}</p>
        <p v-if="resource.unavailable_reason" class="resource-reason">
          {{ resource.unavailable_reason }}
        </p>
        <RouterLink v-if="primaryRoute(resource) !== null" class="resource-cta-link" :to="primaryRoute(resource) ?? undefined">
          {{ primaryCta(resource) }}
        </RouterLink>
        <RouterLink
          v-if="maintenanceRoute(resource) !== null && resourceRoute(resource) !== maintenanceRoute(resource)"
          class="resource-maintenance-link"
          :to="maintenanceRoute(resource) ?? undefined"
        >
          Open maintenance view
        </RouterLink>
        <p v-else-if="resource.available" class="resource-copy">Specialized UI coming soon.</p>
      </article>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { resourceMaintenancePath } from '../genericResource'
import { useAdminApi } from '../api'
import type { ResourceDiscoveryEntry } from '../types'

const client = useAdminApi()

const loading = ref(true)
const error = ref('')
const resources = ref<ResourceDiscoveryEntry[]>([])

onMounted(async () => {
  try {
    resources.value = await client.listResources()
  } catch (loadError) {
    error.value = loadError instanceof Error ? loadError.message : 'Unable to load resources.'
  } finally {
    loading.value = false
  }
})

function resourceRoute(resource: ResourceDiscoveryEntry): string | null {
  if (
    resource.path === '/sessions' ||
    resource.path === '/conversations' ||
    resource.path === '/players' ||
    resource.path === '/map-stats'
  ) {
    return resource.path
  }
  return null
}

function maintenanceRoute(resource: ResourceDiscoveryEntry): string | null {
  if (!resource.available || resource.read_only || resource.schema_url === null) {
    return null
  }
  return resourceMaintenancePath(resource.name)
}

function primaryRoute(resource: ResourceDiscoveryEntry): string | null {
  return resourceRoute(resource) ?? maintenanceRoute(resource)
}

function primaryCta(resource: ResourceDiscoveryEntry): string {
  if (resource.path === '/conversations') {
    return 'Open conversation inbox'
  }
  if (resource.path === '/sessions') {
    return 'Open session review'
  }
  if (resource.path === '/players') {
    return 'Open player review'
  }
  if (resource.path === '/map-stats') {
    return 'Open map stats report'
  }
  return 'Open maintenance view'
}
</script>

<style scoped>
.workspace-shell {
  display: grid;
  gap: 1.5rem;
}

.workspace-header {
  display: grid;
  gap: 0.75rem;
}

.eyebrow {
  margin: 0;
  color: #8c3d1f;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.workspace-header h1 {
  margin: 0;
  font-size: clamp(2.1rem, 4vw, 3.5rem);
}

.workspace-copy,
.workspace-error,
.resource-copy,
.resource-cta,
.resource-path,
.resource-collection,
.resource-reason,
.resource-maintenance-link,
.resource-cta-link {
  margin: 0;
  color: #52606d;
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
}

.resource-card {
  display: grid;
  gap: 0.6rem;
  padding: 1rem;
  border: 1px solid #d9cbb9;
  border-radius: 1rem;
  background: #fffaf2;
  color: inherit;
  text-decoration: none;
}

.resource-card header {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
}

.resource-card h2 {
  margin: 0;
}

.resource-card span,
.resource-cta,
.resource-cta-link {
  color: #8c3d1f;
  font-weight: 700;
}

.resource-cta-link,
.resource-maintenance-link {
  color: #8c3d1f;
  font-weight: 700;
  text-decoration: none;
}

.resource-reason {
  color: #9b1c1c;
}
</style>