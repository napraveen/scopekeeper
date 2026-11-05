/**
 * Wires the event stream into TanStack Query: each event updates the cache directly,
 * then the affected queries refetch in the background.
 */
import { useEffect } from 'react'
import { useQueryClient, type QueryClient, type QueryKey } from '@tanstack/react-query'
import { qk } from '@/lib/api/client'
import { openStream } from '@/lib/api/stream'
import type { DeskState, StreamEvent } from '@/lib/api/types'
import { useConnectionStore, usePulseStore } from '@/stores/ui'

const AFFECTS: Record<string, QueryKey[]> = {
  'desk.handover': [qk.desk],
  'ask.created': [qk.asks, qk.overview()],
  'ask.classified': [qk.asks, qk.overview()],
  'question.asked': [qk.asks],
  'question.answered': [qk.asks, qk.overview()],
  'cr.created': [qk.asks, qk.changeRequests],
  'cr.estimated': [qk.changeRequests],
  'cr.confirmed': [qk.changeRequests],
  'cr.priced': [qk.changeRequests],
  'cr.approved': [qk.changeRequests],
  'co.sent': [qk.changeRequests, qk.asks, qk.overview()],
  'client.decided': [qk.changeRequests, qk.asks, qk.overview()],
  'work.created': [qk.asks],
  'work.pr_opened': [qk.asks],
  'work.preview_ready': [qk.asks],
  'ask.accepted': [qk.asks],
  'plan.updated': [qk.plan],
  'ledger.updated': [qk.overview(), qk.ledger()],
  'room.message': [qk.rooms],
}

function isDeskData(v: unknown): v is { from: DeskState['holder']; to: DeskState['holder'] } {
  return Boolean(v && typeof v === 'object' && 'to' in v)
}

export function applyStreamEvent(client: QueryClient, ev: StreamEvent): void {
  // 1. Direct cache updates.
  client.setQueryData<StreamEvent[]>(qk.events, (prev) =>
    prev ? (prev.some((e) => e.id === ev.id) ? prev : [ev, ...prev]) : prev,
  )
  if (ev.type === 'desk.handover' && isDeskData(ev.data)) {
    const to = ev.data.to
    client.setQueryData<DeskState>(qk.desk, (prev) =>
      prev
        ? { ...prev, holder: to, mode: to === 'scout' ? 'autopilot' : 'copilot', since: ev.ts, nextHolder: to === 'scout' ? 'priya' : 'scout' }
        : prev,
    )
  }
  // 2. Background refetch of what the event touched.
  for (const key of AFFECTS[ev.type] ?? []) void client.invalidateQueries({ queryKey: key })
  if (ev.askId) void client.invalidateQueries({ queryKey: qk.ask(ev.askId) })
  if (ev.crId) void client.invalidateQueries({ queryKey: qk.changeRequest(ev.crId) })
}

export function useLiveStream(): void {
  const client = useQueryClient()
  const retry = useConnectionStore((s) => s.retry)
  useEffect(() => {
    const { setStatus } = useConnectionStore.getState()
    const { bump, clear } = usePulseStore.getState()
    return openStream({
      onEvent(ev) {
        applyStreamEvent(client, ev)
        if (ev.askId) bump(ev.askId)
      },
      onSync() {
        clear()
        void client.invalidateQueries()
      },
      onStatus: setStatus,
    })
  }, [client, retry])
}
