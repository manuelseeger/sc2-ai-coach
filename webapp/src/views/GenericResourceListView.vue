<template>
  <section class="resource-shell">
    <header class="resource-header">
      <div>
        <RouterLink class="back-link" to="/">Back to workspace</RouterLink>
        <p class="eyebrow">Generic Maintenance</p>
        <h1>{{ resource?.title ?? route.params.resourceName }}</h1>
      </div>
      <div v-if="resource" class="capability-list">
        <span v-for="capability in resource.capabilities" :key="capability" class="capability-pill">
          {{ capability }}
        </span>
      </div>
    </header>

    <p v-if="loading" class="resource-copy">Loading resource maintenance view…</p>
    <p v-else-if="error" class="resource-error">{{ error }}</p>

    <template v-else-if="resource && schema && results">
      <section class="panel toolbar-panel">
        <div class="toolbar-row">
          <label>
            <span>Projection</span>
            <select v-model="projection">
              <option v-for="option in schema.available_projections" :key="option" :value="option">
                {{ option }}
              </option>
            </select>
          </label>

          <label>
            <span>Sort</span>
            <input v-model="sort" placeholder="-created_at" />
          </label>

          <RouterLink
            v-if="resource.capabilities.includes('create') && !resource.read_only"
            class="action-link"
            data-testid="create-document-link"
            :to="resourceCreatePath(resource.name)"
          >
            Create document
          </RouterLink>
        </div>

        <div v-if="filterFields.length > 0" class="filter-grid">
          <label v-for="field in filterFields" :key="field.name">
            <span>{{ field.label }}</span>
            <template v-if="field.kind === 'boolean'">
              <select v-model="filterValues[field.name]">
                <option value="">Any</option>
                <option value="true">True</option>
                <option value="false">False</option>
              </select>
            </template>
            <template v-else-if="field.kind === 'select'">
              <select v-model="filterValues[field.name]">
                <option value="">Any</option>
                <option v-for="option in field.options" :key="option" :value="option">
                  {{ option }}
                </option>
              </select>
            </template>
            <template v-else>
              <input v-model="filterValues[field.name]" :type="field.kind === 'number' ? 'number' : 'text'" />
            </template>
          </label>
        </div>

        <div class="toolbar-actions">
          <button type="button" data-testid="apply-filters" @click="applyFilters">Apply filters</button>
          <button type="button" class="button-secondary" @click="resetFilters">Reset filters</button>
        </div>
      </section>

      <section class="panel query-panel">
        <div class="panel-header">
          <div>
            <h2>Advanced query</h2>
            <p class="resource-copy">Use the guarded read-only query endpoint for irregular filtering.</p>
          </div>
          <div class="toolbar-actions">
            <button type="button" data-testid="run-query" @click="runQuery">Run query</button>
            <button type="button" class="button-secondary" @click="resetQuery">Restore list</button>
          </div>
        </div>
        <textarea v-model="queryText" data-testid="query-editor" class="query-editor" spellcheck="false"></textarea>
      </section>

      <section class="panel table-panel">
        <div class="panel-header">
          <div>
            <h2>Documents</h2>
            <p class="resource-copy">
              {{ results.total }} result{{ results.total === 1 ? '' : 's' }} · projection {{ results.projection }}
            </p>
          </div>
          <p class="resource-copy">Page {{ results.page }} of {{ Math.max(results.total_pages, 1) }}</p>
        </div>

        <p v-if="results.items.length === 0" class="resource-copy">No documents matched the current maintenance view.</p>

        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th v-for="key in itemKeys" :key="key">{{ key }}</th>
                <th>Open</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in results.items" :key="documentId(item)">
                <td v-for="key in itemKeys" :key="`${documentId(item)}-${key}`">
                  {{ formatGenericValue(item[key]) }}
                </td>
                <td>
                  <RouterLink class="action-link" :to="resourceDocumentPath(resource.name, documentId(item))">
                    Open
                  </RouterLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { useAdminApi } from '../api'
import {
  coerceFieldValue,
  extractGenericFields,
  formatGenericValue,
  resourceCreatePath,
  resourceDocumentPath,
} from '../genericResource'
import type {
  GenericResourceListResponse,
  GenericResourceQueryRequest,
  GenericResourceSchemaResponse,
  ResourceDiscoveryEntry,
} from '../types'

const client = useAdminApi()
const route = useRoute()

const loading = ref(true)
const error = ref('')
const resource = ref<ResourceDiscoveryEntry | null>(null)
const schema = ref<GenericResourceSchemaResponse | null>(null)
const results = ref<GenericResourceListResponse | null>(null)
const projection = ref('table')
const sort = ref('-created_at')
const queryText = ref('')
const filterValues = reactive<Record<string, string>>({})

const filterFields = computed(() => extractGenericFields(schema.value))
const itemKeys = computed(() => {
  const firstItem = results.value?.items[0]
  if (!firstItem) {
    return [schema.value?.id_field ?? 'id']
  }
  return Object.keys(firstItem)
})

onMounted(loadResource)
watch(() => route.params.resourceName, loadResource)

async function loadResource(): Promise<void> {
  loading.value = true
  error.value = ''
  resource.value = null
  schema.value = null
  results.value = null

  try {
    const resourceName = String(route.params.resourceName)
    const resources = await client.listResources()
    resource.value = resources.find((entry) => entry.name === resourceName) ?? null
    if (resource.value === null) {
      error.value = 'Resource discovery did not include this maintenance target.'
      return
    }
    schema.value = await client.getResourceSchema(resourceName)
    projection.value = schema.value.default_projection
    initializeFilters()
    queryText.value = JSON.stringify(defaultQuery(), null, 2)
    await loadList()
  } catch (loadError) {
    error.value = loadError instanceof Error ? loadError.message : 'Unable to load resource maintenance.'
  } finally {
    loading.value = false
  }
}

async function loadList(): Promise<void> {
  if (resource.value === null) {
    return
  }
  results.value = await client.listResource(resource.value.name, {
    page: 1,
    pageSize: 20,
    sort: sort.value.length > 0 ? sort.value : null,
    projection: projection.value,
    filters: activeFilters(),
  })
}

async function applyFilters(): Promise<void> {
  error.value = ''
  try {
    await loadList()
    queryText.value = JSON.stringify(defaultQuery(), null, 2)
  } catch (actionError) {
    error.value = actionError instanceof Error ? actionError.message : 'Unable to apply maintenance filters.'
  }
}

function resetFilters(): void {
  initializeFilters()
  void applyFilters()
}

async function runQuery(): Promise<void> {
  if (resource.value === null) {
    return
  }
  error.value = ''
  try {
    const request = JSON.parse(queryText.value) as GenericResourceQueryRequest
    results.value = await client.queryResource(resource.value.name, request)
  } catch (actionError) {
    error.value = actionError instanceof Error ? actionError.message : 'Unable to run the maintenance query.'
  }
}

function resetQuery(): void {
  queryText.value = JSON.stringify(defaultQuery(), null, 2)
  void applyFilters()
}

function initializeFilters(): void {
  for (const key of Object.keys(filterValues)) {
    delete filterValues[key]
  }
  for (const field of filterFields.value) {
    filterValues[field.name] = ''
  }
}

function activeFilters(): Record<string, unknown> {
  const filters: Record<string, unknown> = {}
  for (const field of filterFields.value) {
    const rawValue = filterValues[field.name]
    if (rawValue === undefined || rawValue.length === 0) {
      continue
    }
    filters[field.name] = coerceFieldValue(field, rawValue)
  }
  return filters
}

function defaultQuery(): GenericResourceQueryRequest {
  return {
    filter: activeFilters(),
    sort: sort.value.length > 0 ? sortRecord(sort.value) : undefined,
    page: 1,
    page_size: 20,
    projection: projection.value,
  }
}

function sortRecord(value: string): Record<string, number> {
  if (value.length === 0) {
    return {}
  }
  return value.split(',').reduce<Record<string, number>>((result, entry) => {
    const trimmed = entry.trim()
    if (trimmed.length === 0) {
      return result
    }
    if (trimmed.startsWith('-')) {
      result[trimmed.slice(1)] = -1
      return result
    }
    result[trimmed] = 1
    return result
  }, {})
}

function documentId(item: Record<string, unknown>): string {
  if (schema.value === null) {
    return String(item.id ?? '')
  }
  return String(item[schema.value.id_field] ?? item.id ?? '')
}
</script>

<style scoped>
.resource-shell {
  display: grid;
  gap: 1.25rem;
}

.resource-header,
.panel,
.toolbar-row,
.toolbar-actions,
.panel-header {
  display: flex;
}

.resource-header,
.panel,
.query-panel {
  flex-direction: column;
}

.resource-header,
.panel {
  gap: 0.9rem;
}

.resource-header {
  justify-content: space-between;
}

.back-link,
.action-link {
  color: #8c3d1f;
  font-weight: 700;
  text-decoration: none;
}

.eyebrow {
  margin: 0.35rem 0 0;
  color: #8c3d1f;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.resource-header h1,
.panel h2 {
  margin: 0;
}

.capability-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.capability-pill {
  padding: 0.35rem 0.6rem;
  border-radius: 999px;
  background: #f9e0cf;
  color: #8c3d1f;
  font-size: 0.8rem;
  font-weight: 700;
}

.panel {
  padding: 1rem;
  border: 1px solid #d9cbb9;
  border-radius: 1rem;
  background: #fffaf2;
}

.toolbar-row,
.panel-header {
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.75rem;
}

label {
  display: grid;
  gap: 0.35rem;
}

label span,
.resource-copy,
.resource-error {
  color: #52606d;
}

input,
select,
textarea,
button {
  font: inherit;
}

input,
select,
textarea {
  width: 100%;
  padding: 0.7rem 0.8rem;
  border: 1px solid #d9cbb9;
  border-radius: 0.75rem;
  background: #fff;
}

button {
  padding: 0.7rem 1rem;
  border: none;
  border-radius: 999px;
  background: #8c3d1f;
  color: #fffaf2;
  cursor: pointer;
}

.button-secondary {
  background: #ead8c2;
  color: #4b2e1f;
}

.query-editor {
  min-height: 14rem;
  font-family: 'Cascadia Code', 'Fira Code', monospace;
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 0.7rem;
  border-bottom: 1px solid #ead8c2;
  text-align: left;
  vertical-align: top;
}

.resource-error {
  color: #9b1c1c;
}
</style>
