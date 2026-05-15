<template>
  <section class="detail-shell">
    <header class="detail-header">
      <div>
        <RouterLink class="back-link" :to="resourceMaintenancePath(resourceName)">Back to maintenance list</RouterLink>
        <p class="eyebrow">Generic Maintenance</p>
        <h1>{{ createMode ? `Create ${resource?.title ?? resourceName}` : documentTitle }}</h1>
      </div>
      <p v-if="resource" class="detail-copy">
        {{ resource.read_only ? 'Read-only resource' : 'Writable resource' }} · {{ resource.collection ?? 'n/a' }}
      </p>
    </header>

    <p v-if="loading" class="detail-copy">Loading document maintenance view…</p>
    <p v-else-if="error" class="detail-error">{{ error }}</p>

    <template v-else-if="resource && schema">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>Schema-guided edit</h2>
            <p class="detail-copy">Top-level scalar fields are editable here. Complex shapes stay available in the JSON fallback.</p>
          </div>
          <a v-if="resource.schema_url" class="schema-link" :href="resource.schema_url" target="_blank" rel="noreferrer">
            Open schema
          </a>
        </div>

        <div v-if="fields.length > 0" class="field-grid">
          <label v-for="field in fields" :key="field.name">
            <span>{{ field.label }}</span>
            <template v-if="field.kind === 'boolean'">
              <select :value="String(formValues[field.name] ?? '')" @change="updateField(field.name, ($event.target as HTMLSelectElement).value)">
                <option value="true">True</option>
                <option value="false">False</option>
              </select>
            </template>
            <template v-else-if="field.kind === 'select'">
              <select :value="String(formValues[field.name] ?? '')" @change="updateField(field.name, ($event.target as HTMLSelectElement).value)">
                <option v-if="field.nullable" value="">Unset</option>
                <option v-for="option in field.options" :key="option" :value="option">
                  {{ option }}
                </option>
              </select>
            </template>
            <template v-else>
              <input
                :type="field.kind === 'number' ? 'number' : 'text'"
                :value="String(formValues[field.name] ?? '')"
                @input="updateField(field.name, ($event.target as HTMLInputElement).value)"
              />
            </template>
          </label>
        </div>
        <p v-else class="detail-copy">This document shape is too irregular for schema-guided top-level fields. Use the JSON fallback below.</p>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>JSON fallback</h2>
            <p class="detail-copy">Exact maintenance payload used for create, patch, and replace.</p>
          </div>
          <span class="detail-copy">{{ createMode ? 'new document' : currentDocumentId }}</span>
        </div>
        <textarea v-model="rawDocument" data-testid="json-editor" class="json-editor" spellcheck="false"></textarea>
      </section>

      <p v-if="successMessage" class="detail-success">{{ successMessage }}</p>

      <div class="action-row">
        <button v-if="createMode" type="button" data-testid="create-document" :disabled="resource.read_only" @click="createDocument">
          Create document
        </button>
        <template v-else>
          <button type="button" data-testid="patch-document" :disabled="resource.read_only" @click="patchDocument">Patch document</button>
          <button type="button" data-testid="replace-document" class="button-secondary" :disabled="resource.read_only" @click="replaceDocument">
            Replace document
          </button>
          <button type="button" data-testid="delete-document" class="button-danger" :disabled="resource.read_only" @click="deleteDocument">
            Delete document
          </button>
        </template>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { useAdminApi } from '../api'
import {
  coerceFieldValue,
  extractGenericFields,
  formatGenericValue,
  resourceDocumentPath,
  resourceMaintenancePath,
} from '../genericResource'
import type { GenericField } from '../genericResource'
import type { GenericResourceSchemaResponse, ResourceDiscoveryEntry } from '../types'

const client = useAdminApi()
const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const successMessage = ref('')
const resource = ref<ResourceDiscoveryEntry | null>(null)
const schema = ref<GenericResourceSchemaResponse | null>(null)
const rawDocument = ref('{}')
const formValues = reactive<Record<string, string | boolean>>({})

const resourceName = computed(() => String(route.params.resourceName ?? ''))
const currentDocumentId = computed(() => String(route.params.documentId ?? ''))
const createMode = computed(() => route.path.endsWith('/new'))
const fields = computed(() => extractGenericFields(schema.value))
const documentTitle = computed(() => {
  const parsed = safeParseDocument()
  return parsed.id ? `Document ${String(parsed.id)}` : `Document ${currentDocumentId.value}`
})

onMounted(loadDocument)
watch(() => route.fullPath, loadDocument)

async function loadDocument(): Promise<void> {
  loading.value = true
  error.value = ''
  successMessage.value = ''

  try {
    const resources = await client.listResources()
    resource.value = resources.find((entry) => entry.name === resourceName.value) ?? null
    if (resource.value === null) {
      error.value = 'Resource discovery did not include this maintenance target.'
      return
    }
    schema.value = await client.getResourceSchema(resourceName.value)
    if (createMode.value) {
      rawDocument.value = JSON.stringify({}, null, 2)
      syncFormValues({})
      return
    }
    const document = await client.getResource(resourceName.value, currentDocumentId.value, 'detail')
    setDocument(document)
  } catch (loadError) {
    error.value = loadError instanceof Error ? loadError.message : 'Unable to load document maintenance.'
  } finally {
    loading.value = false
  }
}

function setDocument(document: Record<string, unknown>): void {
  rawDocument.value = JSON.stringify(document, null, 2)
  syncFormValues(document)
}

function syncFormValues(document: Record<string, unknown>): void {
  for (const key of Object.keys(formValues)) {
    delete formValues[key]
  }
  for (const field of fields.value) {
    const value = document[field.name]
    if (typeof value === 'boolean') {
      formValues[field.name] = value
      continue
    }
    if (value === null || value === undefined) {
      formValues[field.name] = ''
      continue
    }
    formValues[field.name] = formatGenericValue(value)
  }
}

function updateField(fieldName: string, rawValue: string): void {
  const field = fields.value.find((entry) => entry.name === fieldName)
  if (!field) {
    return
  }
  const draft = safeParseDocument()
  draft[fieldName] = coerceFieldValue(field, rawValue)
  rawDocument.value = JSON.stringify(draft, null, 2)
  syncFormValues(draft)
}

async function createDocument(): Promise<void> {
  if (resource.value === null) {
    return
  }
  error.value = ''
  successMessage.value = ''
  try {
    const created = await client.createResource(resource.value.name, safeParseDocument())
    successMessage.value = 'Document created.'
    const createdId = String(created.id ?? created[schema.value?.id_field ?? 'id'])
    await router.push(resourceDocumentPath(resource.value.name, createdId))
  } catch (actionError) {
    error.value = actionError instanceof Error ? actionError.message : 'Unable to create document.'
  }
}

async function patchDocument(): Promise<void> {
  if (resource.value === null) {
    return
  }
  error.value = ''
  successMessage.value = ''
  try {
    const payload = safeParseDocument()
    delete payload.id
    const saved = await client.patchResource(resource.value.name, currentDocumentId.value, payload)
    setDocument(saved)
    successMessage.value = 'Document patched.'
  } catch (actionError) {
    error.value = actionError instanceof Error ? actionError.message : 'Unable to patch document.'
  }
}

async function replaceDocument(): Promise<void> {
  if (resource.value === null) {
    return
  }
  error.value = ''
  successMessage.value = ''
  try {
    const payload = safeParseDocument()
    payload.id = currentDocumentId.value
    const saved = await client.replaceResource(resource.value.name, currentDocumentId.value, payload)
    setDocument(saved)
    successMessage.value = 'Document replaced.'
  } catch (actionError) {
    error.value = actionError instanceof Error ? actionError.message : 'Unable to replace document.'
  }
}

async function deleteDocument(): Promise<void> {
  if (resource.value === null) {
    return
  }
  error.value = ''
  successMessage.value = ''
  try {
    await client.deleteResource(resource.value.name, currentDocumentId.value)
    await router.push(resourceMaintenancePath(resource.value.name))
  } catch (actionError) {
    error.value = actionError instanceof Error ? actionError.message : 'Unable to delete document.'
  }
}

function safeParseDocument(): Record<string, unknown> {
  const parsed = JSON.parse(rawDocument.value) as unknown
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('Document editor must contain a JSON object.')
  }
  return parsed as Record<string, unknown>
}
</script>

<style scoped>
.detail-shell {
  display: grid;
  gap: 1.25rem;
}

.detail-header,
.panel,
.panel-header,
.action-row {
  display: flex;
}

.detail-header,
.panel {
  flex-direction: column;
  gap: 0.9rem;
}

.detail-header {
  justify-content: space-between;
}

.back-link,
.schema-link {
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

.detail-header h1,
.panel h2 {
  margin: 0;
}

.detail-copy,
.detail-error,
.detail-success {
  margin: 0;
  color: #52606d;
}

.panel {
  padding: 1rem;
  border: 1px solid #d9cbb9;
  border-radius: 1rem;
  background: #fffaf2;
}

.panel-header,
.action-row {
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
}

label {
  display: grid;
  gap: 0.35rem;
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

.button-danger,
.detail-error {
  color: #9b1c1c;
}

.button-danger {
  background: #f7d7d4;
}

.detail-success {
  color: #1f6f43;
}

.json-editor {
  min-height: 18rem;
  font-family: 'Cascadia Code', 'Fira Code', monospace;
}
</style>
