import type { ConversationStatus, ConversationTrigger } from './types'

export function formatTrigger(trigger: ConversationTrigger): string {
  return trigger
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function formatStatus(status: ConversationStatus): string {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

export function formatUtcDate(value: string): string {
  return new Intl.DateTimeFormat('en', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'UTC',
  }).format(new Date(value))
}