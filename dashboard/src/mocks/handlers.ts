/**
 * MSW handlers for every endpoint in the contract, served from the in-memory db.
 * Shared by the browser worker (`browser.ts`) and the tests (`node.ts`).
 */
import { delay, http, HttpResponse } from 'msw'
import type { OptionKey } from '@/lib/api/types'
import { computeOverview, db, findCr } from './db'
import { getEngine } from './engine'
import { CLAUSES, PROJECT, slack } from './seed'
import { approveChangeRequest } from './story'

const LATENCY = import.meta.env.MODE === 'test' ? 0 : 120

const nowIso = () => {
  const e = getEngine()
  return new Date(e ? e.now : Date.now()).toISOString()
}

function notFound(what: string) {
  return HttpResponse.json({ detail: `${what} not found` }, { status: 404 })
}

export const handlers = [
  http.get('*/api/health', () =>
    HttpResponse.json({ ok: true, switch: 'connected', serverTime: nowIso() }),
  ),

  http.get('*/api/overview', async ({ request }) => {
    await delay(LATENCY)
    const month = new URL(request.url).searchParams.get('month') ?? PROJECT.month
    return HttpResponse.json(computeOverview(db.current, month))
  }),

  http.get('*/api/desk', async () => {
    await delay(LATENCY)
    return HttpResponse.json(db.current.desk)
  }),

  http.get('*/api/asks', async ({ request }) => {
    await delay(LATENCY)
    const p = new URL(request.url).searchParams
    let items = [...db.current.asks].sort((a, b) => b.createdAt.localeCompare(a.createdAt))
    const category = p.get('category')
    const status = p.get('status')
    const since = p.get('since')
    const q = p.get('q')?.toLowerCase()
    if (category) items = items.filter((a) => a.category === category)
    if (status) items = items.filter((a) => a.status === status)
    if (since) items = items.filter((a) => new Date(a.createdAt) >= new Date(since))
    if (q) items = items.filter((a) => `${a.id} ${a.quote}`.toLowerCase().includes(q))
    return HttpResponse.json({ items })
  }),

  http.get('*/api/asks/:id', async ({ params }) => {
    await delay(LATENCY)
    const d = db.current
    const ask = d.asks.find((a) => a.id === params.id)
    if (!ask) return notFound('Ask')
    return HttpResponse.json({
      ...ask,
      question: d.questions.find((q) => q.askId === ask.id),
      events: d.events.filter((e) => e.askId === ask.id).sort((a, b) => a.ts.localeCompare(b.ts)),
      workItems: d.workItems.filter((w) => w.askId === ask.id),
    })
  }),

  http.post('*/api/asks/:id/goodwill', async ({ params, request }) => {
    const d = db.current
    const ask = d.asks.find((a) => a.id === params.id)
    if (!ask) return notFound('Ask')
    const body = (await request.json()) as { hours?: number }
    const hours = body.hours ?? 1
    d.goodwillUsedHours += hours
    d.ledger.push({
      date: nowIso(),
      ref: ask.id,
      title: ask.quote,
      hours,
      amountCents: 0,
      approvedBy: 'priya',
      kind: 'goodwill',
      link: slack('acme-intake'),
    })
    return HttpResponse.json(ask)
  }),

  http.get('*/api/change-requests', async () => {
    await delay(LATENCY)
    return HttpResponse.json({ items: db.current.changeRequests.map(({ sentAt: _s, ...cr }) => cr) })
  }),

  http.get('*/api/change-requests/:id', async ({ params }) => {
    await delay(LATENCY)
    const d = db.current
    const cr = d.changeRequests.find((c) => c.id === params.id)
    if (!cr) return notFound('Change request')
    const { sentAt: _s, ...rest } = cr
    return HttpResponse.json({
      ...rest,
      events: d.events.filter((e) => e.crId === cr.id).sort((a, b) => a.ts.localeCompare(b.ts)),
      workItems: d.workItems.filter((w) => w.crId === cr.id || w.askId === cr.askId),
    })
  }),

  http.post('*/api/change-requests/:id/approve', async ({ params, request }) => {
    await delay(LATENCY)
    const d = db.current
    const id = String(params.id)
    if (!d.changeRequests.some((c) => c.id === id)) return notFound('Change request')
    const body = (await request.json()) as { options?: OptionKey[] }
    const keys = body.options ?? []
    const cr = findCr(d, id)
    const engine = getEngine()
    const apply = () => {
      approveChangeRequest(d, id, keys, 'priya', nowIso())
      cr.status = 'sent'
      cr.sentAt ??= nowIso()
      const ask = d.asks.find((a) => a.id === cr.askId)
      if (ask) ask.status = 'change_sent'
    }
    const text =
      keys.length === cr.options.length && keys.length > 1
        ? `Priya approved all ${keys.length === 4 ? 'four' : keys.length} options for ${id}.`
        : `Priya approved option${keys.length > 1 ? 's' : ''} ${keys.join(', ')} for ${id}.`
    if (engine) {
      engine.emitAdHoc({ type: 'cr.approved', actor: 'priya', text, crId: id, askId: cr.askId, roomId: cr.room.room, link: cr.room }, apply)
      engine.emitAdHoc({
        type: 'co.sent',
        actor: 'priya',
        text: `Priya sent Sam change order ${id} with option${keys.length > 1 ? 's' : ''} ${keys.join(', ')}.`,
        crId: id,
        askId: cr.askId,
        roomId: 'acme-client',
        link: { app: 'discord', room: 'acme-client', url: 'https://discord.com/channels/acme-hq/acme-client' },
      })
    } else apply()
    const { sentAt: _s, ...rest } = cr
    return HttpResponse.json(rest)
  }),

  http.post('*/api/change-requests/:id/decline', async ({ params }) => {
    const cr = db.current.changeRequests.find((c) => c.id === params.id)
    if (!cr) return notFound('Change request')
    Object.assign(cr, { status: 'closed', clientChoice: 'DECLINE', decidedAt: nowIso() })
    return HttpResponse.json(cr)
  }),

  http.patch('*/api/change-requests/:id/options/:key', async ({ params, request }) => {
    const cr = db.current.changeRequests.find((c) => c.id === params.id)
    const opt = cr?.options.find((o) => o.key === params.key)
    if (!cr || !opt) return notFound('Option')
    const body = (await request.json()) as { priceCents: number }
    opt.priceCents = body.priceCents
    return HttpResponse.json(cr)
  }),

  /** Contract addition: recent events, newest first. */
  http.get('*/api/events', async ({ request }) => {
    await delay(LATENCY)
    const limit = Number(new URL(request.url).searchParams.get('limit') ?? 60)
    const items = [...db.current.events].sort((a, b) => b.ts.localeCompare(a.ts)).slice(0, limit)
    return HttpResponse.json({ items })
  }),

  http.get('*/api/ledger', async ({ request }) => {
    await delay(LATENCY)
    const month = new URL(request.url).searchParams.get('month') ?? PROJECT.month
    return HttpResponse.json({ overview: computeOverview(db.current, month), entries: db.current.ledger })
  }),

  http.get('*/api/invoice', () => {
    const rows = db.current.ledger
      .filter((e) => e.kind === 'change_order')
      .map((e) => `${e.date},${e.ref},"${e.title}",${e.hours},${(e.amountCents / 100).toFixed(2)}`)
    return new HttpResponse(['date,ref,title,hours,amount', ...rows].join('\n'), {
      headers: { 'Content-Type': 'text/csv' },
    })
  }),

  http.get('*/api/renewal', () =>
    HttpResponse.json([
      {
        theme: 'Reporting',
        askIds: ['ASK-0004', 'ASK-0005', 'ASK-0006', 'ASK-0009'],
        hours: 65,
        proposal: '4 reporting changes asked for this quarter: propose a reporting add-on',
      },
    ]),
  ),

  http.get('*/api/config/:name', ({ params }) => {
    switch (params.name) {
      case 'plan':
        return HttpResponse.json(db.current.plan)
      case 'scope-map':
        return HttpResponse.json({ clauses: CLAUSES, warrantyDays: PROJECT.warrantyDays })
      case 'rate-card':
        return HttpResponse.json({
          currency: PROJECT.currency,
          rateCents: PROJECT.rateCents,
          contingency: PROJECT.contingency,
          roundingCents: PROJECT.roundingCents,
        })
      case 'envelope':
        return HttpResponse.json(PROJECT.envelope)
      case 'schedule':
        return HttpResponse.json({ agencyDayStart: '09:30', agencyDayEnd: '19:00', timezone: 'Asia/Kolkata' })
      default:
        return notFound('Config')
    }
  }),

  http.put('*/api/config/:name', async ({ request }) => HttpResponse.json(await request.json())),

  http.get('*/api/rooms', () => {
    const d = db.current
    const changeRooms = d.changeRequests
      .filter((c) => c.status !== 'closed' && c.status !== 'decided')
      .map((c) => ({
        id: c.room.room,
        name: c.room.room,
        app: 'slack' as const,
        kind: 'change' as const,
        members: d.rooms.rooms.find((r) => r.id === 'acme-intake')?.members ?? [],
        roles: [{ name: '@delivery-lead', holder: 'ravi' }],
        references: [c.id, c.askId],
      }))
    return HttpResponse.json({ rooms: [...d.rooms.rooms, ...changeRooms], links: d.rooms.links })
  }),

  http.get('*/api/public/co/:id', ({ params }) => {
    const cr = db.current.changeRequests.find((c) => c.id === params.id)
    if (!cr) return notFound('Change order')
    return HttpResponse.json({ ...cr, client: PROJECT.client, agency: PROJECT.agency })
  }),

  http.post('*/api/demo/flip', () => {
    getEngine()?.flipNow()
    return HttpResponse.json({ ok: true })
  }),
  http.post('*/api/demo/morning', () => {
    getEngine()?.morningNow()
    return HttpResponse.json({ ok: true })
  }),
  http.post('*/api/demo/clock', () => HttpResponse.json({ ok: true, now: nowIso() })),
]
