/**
 * The one place where backend shapes are adapted to the contract in `types.ts`.
 * The backend (Python) may answer in snake_case; keys are camelised here, and any
 * other differences should be handled in the specific adapter below.
 */
import type {
  Ask,
  AskPage,
  ChangeRequest,
  DeskState,
  Health,
  LedgerEntry,
  Overview,
  Plan,
  RoomMap,
  StreamEvent,
} from './types'

type Json = string | number | boolean | null | Json[] | { [key: string]: Json }

function camel(key: string): string {
  return key.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase())
}

/** Category and option keys like `OUT_OF_SCOPE` stay untouched: only object keys change. */
export function camelize(value: unknown): Json {
  if (Array.isArray(value)) return value.map(camelize)
  if (value && typeof value === 'object') {
    const out: { [key: string]: Json } = {}
    for (const [k, v] of Object.entries(value)) {
      // Record<Category, number> keys are upper-case and must not change.
      out[/^[A-Z_]+$/.test(k) ? k : camel(k)] = camelize(v)
    }
    return out
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return value
  return null
}

function as<T>(raw: unknown): T {
  return camelize(raw) as unknown as T
}

export const adaptHealth = (raw: unknown) => as<Health>(raw)
export const adaptOverview = (raw: unknown) => as<Overview>(raw)
export const adaptDesk = (raw: unknown) => as<DeskState>(raw)
export const adaptAsk = (raw: unknown) => as<Ask>(raw)
export const adaptChangeRequest = (raw: unknown) => as<ChangeRequest>(raw)
export const adaptPlan = (raw: unknown) => as<Plan>(raw)
export const adaptRoomMap = (raw: unknown) => as<RoomMap>(raw)
export const adaptLedgerEntry = (raw: unknown) => as<LedgerEntry>(raw)

export function adaptAskPage(raw: unknown): AskPage {
  const v = camelize(raw)
  if (Array.isArray(v)) return { items: v as unknown as Ask[] }
  return v as unknown as AskPage
}

export function adaptList<T>(raw: unknown, key: string): T[] {
  const v = camelize(raw)
  if (Array.isArray(v)) return v as unknown as T[]
  if (v && typeof v === 'object' && !Array.isArray(v) && Array.isArray(v[key])) return v[key] as unknown as T[]
  return []
}

export function adaptStreamEvent(raw: unknown, sseEventName?: string): StreamEvent {
  const e = as<StreamEvent>(raw)
  if (!e.type && sseEventName) e.type = sseEventName
  return e
}
