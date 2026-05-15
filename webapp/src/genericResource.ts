import type { GenericResourceSchemaResponse } from './types'

export interface GenericField {
  name: string
  label: string
  kind: 'text' | 'number' | 'boolean' | 'select'
  options: string[]
  nullable: boolean
}

export function resourceMaintenancePath(resourceName: string): string {
  return `/resources/${encodeURIComponent(resourceName)}`
}

export function resourceDocumentPath(resourceName: string, documentId: string): string {
  return `${resourceMaintenancePath(resourceName)}/${encodeURIComponent(documentId)}`
}

export function resourceCreatePath(resourceName: string): string {
  return `${resourceMaintenancePath(resourceName)}/new`
}

export function extractGenericFields(schemaResponse: GenericResourceSchemaResponse | null): GenericField[] {
  const properties = schemaProperties(schemaResponse?.schema)
  return Object.entries(properties)
    .filter(([name, property]) => isEditableScalar(name, property))
    .map(([name, property]) => buildField(name, property))
}

export function coerceFieldValue(field: GenericField, value: string | boolean): unknown {
  if (field.kind === 'boolean') {
    if (typeof value === 'boolean') {
      return value
    }
    return value === 'true'
  }
  if (field.kind === 'number') {
    if (typeof value === 'boolean') {
      return Number(value)
    }
    if (value.length === 0) {
      return field.nullable ? null : 0
    }
    return Number(value)
  }
  if (typeof value === 'boolean') {
    return String(value)
  }
  if (value.length === 0 && field.nullable) {
    return null
  }
  return value
}

export function formatGenericValue(value: unknown): string {
  if (value === null) {
    return 'null'
  }
  if (value === undefined) {
    return ''
  }
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return JSON.stringify(value)
}

function schemaProperties(schema: Record<string, unknown> | undefined): Record<string, Record<string, unknown>> {
  if (!schema) {
    return {}
  }
  const properties = schema.properties
  if (!properties || typeof properties !== 'object' || Array.isArray(properties)) {
    return {}
  }
  return properties as Record<string, Record<string, unknown>>
}

function isEditableScalar(name: string, property: Record<string, unknown>): boolean {
  if (['id', 'created_at', 'updated_at'].includes(name)) {
    return false
  }
  const types = schemaTypes(property)
  if (types.includes('object') || types.includes('array')) {
    return false
  }
  return types.includes('string') || types.includes('number') || types.includes('integer') || types.includes('boolean')
}

function buildField(name: string, property: Record<string, unknown>): GenericField {
  const types = schemaTypes(property)
  const options = Array.isArray(property.enum)
    ? property.enum.filter((value): value is string => typeof value === 'string')
    : []
  if (options.length > 0) {
    return {
      name,
      label: titleCase(name),
      kind: 'select',
      options,
      nullable: types.includes('null'),
    }
  }
  if (types.includes('boolean')) {
    return {
      name,
      label: titleCase(name),
      kind: 'boolean',
      options: [],
      nullable: false,
    }
  }
  if (types.includes('number') || types.includes('integer')) {
    return {
      name,
      label: titleCase(name),
      kind: 'number',
      options: [],
      nullable: types.includes('null'),
    }
  }
  return {
    name,
    label: titleCase(name),
    kind: 'text',
    options: [],
    nullable: types.includes('null'),
  }
}

function schemaTypes(property: Record<string, unknown>): string[] {
  const rawType = property.type
  if (Array.isArray(rawType)) {
    return rawType.filter((value): value is string => typeof value === 'string')
  }
  if (typeof rawType === 'string') {
    return [rawType]
  }
  return []
}

function titleCase(value: string): string {
  return value
    .split(/[-_]/g)
    .filter((part) => part.length > 0)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(' ')
}
