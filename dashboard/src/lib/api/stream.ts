/**
 * The live event stream. Live mode reads server-sent events from `/api/stream` with
 * `@microsoft/fetch-event-source` (so the token travels in a header). Mock mode plugs the
 * in-browser story engine into the exact same interface.
 */
import { fetchEventSource } from '@microsoft/fetch-event-source'
import { API_BASE_URL, API_MODE, getApiToken } from '@/lib/config'
import { adaptStreamEvent } from './adapters'
import type { StreamEvent } from './types'

export type StreamStatus = 'connecting' | 'open' | 'closed' | 'error'

export interface StreamHandlers {
  onEvent(event: StreamEvent): void
  /** State changed wholesale (reset, seek); refetch everything. */
  onSync(): void
  onStatus(status: StreamStatus): void
}

export interface StreamSource {
  subscribe(handlers: StreamHandlers): () => void
}

let mockSource: StreamSource | null = null

export function setMockStreamSource(source: StreamSource): void {
  mockSource = source
}

class FatalError extends Error {}

function liveSource(): StreamSource {
  return {
    subscribe(h) {
      const ctrl = new AbortController()
      h.onStatus('connecting')
      const token = getApiToken()
      void fetchEventSource(`${API_BASE_URL}/api/stream`, {
        signal: ctrl.signal,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        openWhenHidden: true,
        async onopen(res) {
          if (res.ok) {
            h.onStatus('open')
            h.onSync()
            return
          }
          if (res.status === 401 || res.status === 403) throw new FatalError('Unauthorised')
          throw new Error(`Stream failed: ${res.status}`)
        },
        onmessage(msg) {
          if (!msg.data) return
          try {
            const parsed: unknown = JSON.parse(msg.data)
            h.onEvent(adaptStreamEvent(parsed, msg.event))
          } catch {
            // Ignore malformed frames; the next refetch heals the cache.
          }
        },
        onclose() {
          h.onStatus('closed')
          throw new Error('Stream closed')
        },
        onerror(err) {
          h.onStatus('error')
          if (err instanceof FatalError) throw err
          return 5000 // retry in 5 s
        },
      }).catch(() => h.onStatus('error'))
      return () => ctrl.abort()
    },
  }
}

export function openStream(handlers: StreamHandlers): () => void {
  if (API_MODE === 'mock') {
    if (!mockSource) {
      handlers.onStatus('error')
      return () => undefined
    }
    return mockSource.subscribe(handlers)
  }
  return liveSource().subscribe(handlers)
}
