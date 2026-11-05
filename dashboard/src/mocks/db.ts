/**
 * In-memory database behind the MSW handlers. The story engine mutates it; handlers read it.
 * Everything is derived from `seed.ts` and can be reset at any time.
 */
import type {
  Ask,
  Category,
  DeskState,
  LedgerEntry,
  Overview,
  Plan,
  Question,
  RoomMap,
  StreamEvent,
  WorkItem,
} from '@/lib/api/types'
import {
  ASKS,
  CHANGE_REQUESTS,
  DECISION_MINUTES,
  DESK,
  HISTORY_EVENTS,
  LEDGER,
  PLAN,
  PROJECT,
  QUESTIONS,
  ROOMS,
  WORK_ITEMS,
  type DbChangeRequest,
} from './seed'

export interface MockDb {
  asks: Ask[]
  questions: Question[]
  changeRequests: DbChangeRequest[]
  workItems: WorkItem[]
  ledger: LedgerEntry[]
  plan: Plan
  rooms: RoomMap
  desk: DeskState
  events: StreamEvent[]
  decisionMinutes: number[]
  goodwillUsedHours: number
}

function fresh(): MockDb {
  return structuredClone({
    asks: ASKS,
    questions: QUESTIONS,
    changeRequests: CHANGE_REQUESTS,
    workItems: WORK_ITEMS,
    ledger: LEDGER,
    plan: PLAN,
    rooms: ROOMS,
    desk: DESK,
    events: HISTORY_EVENTS,
    decisionMinutes: DECISION_MINUTES,
    goodwillUsedHours: 2,
  })
}

export const db: { current: MockDb } = { current: fresh() }

export function resetDb(): void {
  db.current = fresh()
}

// ---------------------------------------------------------------- helpers used by the story

export function findAsk(d: MockDb, id: string): Ask {
  const a = d.asks.find((x) => x.id === id)
  if (!a) throw new Error(`Unknown ask ${id}`)
  return a
}

export function findCr(d: MockDb, id: string): DbChangeRequest {
  const c = d.changeRequests.find((x) => x.id === id)
  if (!c) throw new Error(`Unknown change request ${id}`)
  return c
}

export function findWork(d: MockDb, id: string): WorkItem {
  const w = d.workItems.find((x) => x.id === id)
  if (!w) throw new Error(`Unknown work item ${id}`)
  return w
}

export function upsert<T extends { id: string }>(list: T[], item: T): void {
  const i = list.findIndex((x) => x.id === item.id)
  if (i === -1) list.push(item)
  else list[i] = item
}

function median(values: number[]): number {
  if (values.length === 0) return 0
  const s = [...values].sort((a, b) => a - b)
  const mid = Math.floor(s.length / 2)
  return s.length % 2 ? s[mid]! : Math.round((s[mid - 1]! + s[mid]!) / 2)
}

function inMonth(iso: string | undefined, month: string): boolean {
  if (!iso) return false
  // Months are counted in the agency's zone (IST); ISO strings in the seed carry +05:30.
  const d = new Date(iso)
  const ist = new Date(d.getTime() + 5.5 * 3600_000)
  return ist.toISOString().slice(0, 7) === month
}

const EMPTY_CATEGORIES: Record<Category, number> = {
  DEFECT: 0,
  IN_SCOPE: 0,
  UNCLEAR: 0,
  OUT_OF_SCOPE: 0,
  DUPLICATE: 0,
  ALREADY_DECIDED: 0,
}

export function computeOverview(d: MockDb, month: string = PROJECT.month): Overview {
  const revenue = d.ledger
    .filter((e) => e.kind === 'change_order' && inMonth(e.date, month))
    .reduce((sum, e) => sum + e.amountCents, 0)

  const changeOrders = { sent: 0, approved: 0, pending: 0, swaps: 0 }
  for (const cr of d.changeRequests) {
    if (!inMonth(cr.sentAt, month)) continue
    changeOrders.sent += 1
    const choice = cr.clientChoice
    if (!choice) changeOrders.pending += 1
    else if (choice !== 'DECLINE') {
      const opt = cr.options.find((o) => o.key === choice)
      if (opt?.swapIn) changeOrders.swaps += 1
      else changeOrders.approved += 1
    }
  }

  const asksByCategory = { ...EMPTY_CATEGORIES }
  for (const a of d.asks) {
    if (a.category && inMonth(a.createdAt, month)) asksByCategory[a.category] += 1
  }

  return {
    month,
    revenueProtectedCents: revenue,
    changeOrders,
    goodwill: { usedHours: d.goodwillUsedHours, bucketHours: PROJECT.goodwillBucketHours },
    medianAskToDecisionMinutes: median(d.decisionMinutes),
    asksByCategory,
  }
}
