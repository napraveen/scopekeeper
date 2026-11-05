import { setupWorker } from 'msw/browser'
import { registerDemoController } from '@/lib/demo'
import { setMockStreamSource } from '@/lib/api/stream'
import { startEngine } from './engine'
import { handlers } from './handlers'

/**
 * Boots mock mode: the MSW service worker for REST, and the story engine for the stream.
 * URL options: `?speed=600` sets the story speed, `?paused` starts paused.
 */
export async function startMocks(): Promise<void> {
  const worker = setupWorker(...handlers)
  await worker.start({
    onUnhandledFrame: 'bypass',
    quiet: true,
    serviceWorker: { url: `${import.meta.env.BASE_URL}mockServiceWorker.js` },
  })

  const params = new URLSearchParams(window.location.search)
  const speedParam = Number(params.get('speed'))
  const engine = startEngine({
    speed: [1, 10, 60, 600].includes(speedParam) ? speedParam : 60,
    autoplay: !params.has('paused'),
  })
  setMockStreamSource(engine)
  registerDemoController(engine)
}
