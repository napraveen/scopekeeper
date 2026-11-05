import type { Member } from '@/lib/api/types'

/** The people and agents, shown the same way everywhere (FRONTEND_PROMPT §2). */
export interface Person extends Member {
  title: string
  initial: string
  app: 'discord' | 'slack'
}

export const PEOPLE: Record<string, Person> = {
  sam: { id: 'sam', name: 'Sam', kind: 'person', side: 'client', title: 'Product owner at Acme', initial: 'S', app: 'discord' },
  priya: { id: 'priya', name: 'Priya', kind: 'person', side: 'agency', title: 'Account manager', initial: 'P', app: 'slack' },
  ravi: { id: 'ravi', name: 'Ravi', kind: 'person', side: 'agency', title: 'Delivery lead', initial: 'R', app: 'slack' },
  aisha: { id: 'aisha', name: 'Aisha', kind: 'person', side: 'agency', title: 'Developer', initial: 'A', app: 'slack' },
  scout: { id: 'scout', name: 'Scout', kind: 'agent', side: 'agency', vendor: 'OpenCode', title: 'Client-desk agent', initial: 'Sc', app: 'slack' },
  clerk: { id: 'clerk', name: 'Clerk', kind: 'agent', side: 'agency', vendor: 'Custom', title: 'Contract-keeper agent', initial: 'Cl', app: 'slack' },
  estimator: { id: 'estimator', name: 'Estimator', kind: 'agent', side: 'agency', vendor: 'Claude Code', title: 'Estimates from the code', initial: 'Es', app: 'slack' },
  builder: { id: 'builder', name: 'Builder', kind: 'agent', side: 'agency', vendor: 'Codex', title: 'Builds approved work', initial: 'Bu', app: 'slack' },
}

export function person(id: string | undefined): Person {
  if (id && PEOPLE[id]) return PEOPLE[id]
  const name = id ? id.charAt(0).toUpperCase() + id.slice(1) : 'Someone'
  return { id: id ?? 'unknown', name, kind: 'person', side: 'agency', title: '', initial: name.charAt(0), app: 'slack' }
}
