/**
 * Every backend call lives here. Mock mode uses the same calls; MSW answers them.
 */
import { API_BASE_URL, getApiToken } from '@/lib/config'
import {
  adaptAsk,
  adaptAskPage,
  adaptChangeRequest,
  adaptDesk,
  adaptHealth,
  adaptList,
  adaptOverview,
  adaptPlan,
  adaptRoomMap,
  adaptStreamEvent,
} from './adapters'
import type {
  Ask,
  AskPage,
  ChangeRequest,
  DeskState,
  Health,
  LedgerEntry,
  OptionKey,
  Overview,
  Plan,
  Question,
  RoomMap,
  ScopeMap,
  StreamEvent,
  WorkItem,
} from './types'

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request(path: string, init: RequestInit = {}): Promise<unknown> {
  const token = getApiToken()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`
    try {
      const body = (await res.json()) as { detail?: string; message?: string }
      message = body.detail ?? body.message ?? message
    } catch {
      // Not JSON; keep the status line.
    }
    throw new ApiError(res.status, message)
  }
  if (res.status === 204) return null
  return res.json()
}

export const currentMonth = '2026-11'

export interface AskDetail extends Ask {
  question?: Question
  events: StreamEvent[]
  workItems: WorkItem[]
}

export const api = {
  health: async (): Promise<Health> => adaptHealth(await request('/api/health')),
  overview: async (month = currentMonth): Promise<Overview> =>
    adaptOverview(await request(`/api/overview?month=${month}`)),
  desk: async (): Promise<DeskState> => adaptDesk(await request('/api/desk')),
  asks: async (params: Record<string, string> = {}): Promise<AskPage> =>
    adaptAskPage(await request(`/api/asks?${new URLSearchParams(params).toString()}`)),
  ask: async (id: string): Promise<AskDetail> => {
    const raw = await request(`/api/asks/${id}`)
    return adaptAsk(raw) as AskDetail
  },
  changeRequests: async (): Promise<ChangeRequest[]> =>
    adaptList<ChangeRequest>(await request('/api/change-requests'), 'items').map((c) => adaptChangeRequest(c)),
  changeRequest: async (id: string): Promise<ChangeRequest> =>
    adaptChangeRequest(await request(`/api/change-requests/${id}`)),
  approve: async (id: string, options: OptionKey[]): Promise<ChangeRequest> =>
    adaptChangeRequest(
      await request(`/api/change-requests/${id}/approve`, { method: 'POST', body: JSON.stringify({ options }) }),
    ),
  decline: async (id: string, reason: string): Promise<ChangeRequest> =>
    adaptChangeRequest(
      await request(`/api/change-requests/${id}/decline`, { method: 'POST', body: JSON.stringify({ reason }) }),
    ),
  /** Contract addition: recent stream events, newest first, to seed the activity feed. */
  events: async (limit = 60): Promise<StreamEvent[]> =>
    adaptList<unknown>(await request(`/api/events?limit=${limit}`), 'items').map((e) => adaptStreamEvent(e)),
  ledger: async (month = currentMonth): Promise<{ overview: Overview; entries: LedgerEntry[] }> => {
    const raw = (await request(`/api/ledger?month=${month}`)) as { overview: unknown; entries: unknown }
    return { overview: adaptOverview(raw.overview), entries: adaptList<LedgerEntry>(raw.entries, 'entries') }
  },
  plan: async (): Promise<Plan> => adaptPlan(await request('/api/config/plan')),
  scope: async (): Promise<ScopeMap> => (await request('/api/config/scope-map')) as ScopeMap,
  rooms: async (): Promise<RoomMap> => adaptRoomMap(await request('/api/rooms')),
  demo: {
    flip: () => request('/api/demo/flip', { method: 'POST' }),
    morning: () => request('/api/demo/morning', { method: 'POST' }),
    clock: (body: Record<string, unknown>) => request('/api/demo/clock', { method: 'POST', body: JSON.stringify(body) }),
  },
}

/** TanStack Query keys, in one place so the stream can update and invalidate them. */
export const qk = {
  health: ['health'] as const,
  overview: (month = currentMonth) => ['overview', month] as const,
  desk: ['desk'] as const,
  asks: ['asks'] as const,
  ask: (id: string) => ['asks', id] as const,
  changeRequests: ['change-requests'] as const,
  changeRequest: (id: string) => ['change-requests', id] as const,
  events: ['events'] as const,
  ledger: (month = currentMonth) => ['ledger', month] as const,
  plan: ['plan'] as const,
  scope: ['scope'] as const,
  rooms: ['rooms'] as const,
}
