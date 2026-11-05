import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import {
  MessageSquare,
  Printer,
  ToggleRight,
} from 'lucide-react'
import { Money } from '@/components/Money'
import { Button } from '@/components/ui/button'
import { formatHours } from '@/lib/format'

interface PublicChangeOrderData {
  id: string
  title: string
  client: string
  agency: string
  status: string
  createdAt: string
  clientChoice?: string
  options: {
    key: string
    label: string
    description: string
    hours: number
    priceCents: number
    shiftDays: number
    newDue?: string
    swapIn?: string
    swapOut?: string[]
  }[]
}

export function PublicChangeOrderPage() {
  const { id = 'CR-004' } = useParams()
  const [data, setData] = useState<PublicChangeOrderData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`/api/public/co/${id}`)
      .then((res) => res.json())
      .then((d) => {
        setData(d)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  const order = data ?? {
    id: 'CR-004',
    title: 'Android app',
    client: 'Acme Inc.',
    agency: 'Pixel & Co',
    status: 'sent',
    createdAt: '2026-11-05T20:31:00+05:30',
    clientChoice: undefined,
    options: [
      {
        key: 'A',
        label: 'Add it now',
        description: 'Build full Android app in this phase; moves M2 due date to Dec 24.',
        hours: 200,
        priceCents: 1035000,
        shiftDays: 12,
        newDue: '2026-12-24',
      },
      {
        key: 'B',
        label: 'Next phase',
        description: 'Build full Android app in next phase; no milestone impact now.',
        hours: 200,
        priceCents: 1035000,
        shiftDays: 0,
      },
      {
        key: 'C',
        label: 'View-only now',
        description: 'View-only version for board meeting; M2 moves 3 days.',
        hours: 56,
        priceCents: 265000,
        shiftDays: 3,
        newDue: '2026-12-15',
      },
      {
        key: 'D',
        label: 'Scope Swap ($0)',
        description: 'View-only app in place of unstarted I9 (Admin analytics dashboard). Zero cost, zero date change.',
        hours: 56,
        priceCents: 0,
        shiftDays: 0,
        swapIn: 'View-only Android app',
        swapOut: ['I9'],
      },
    ],
  }

  return (
    <div className="min-h-screen bg-muted/20 py-8 px-4 sm:px-6 lg:px-8 print:p-0 print:bg-white text-foreground font-sans">
      <div className="max-w-3xl mx-auto rounded-2xl border border-border bg-card p-6 sm:p-10 shadow-sm print:border-none print:shadow-none print:p-0 space-y-8">
        {/* Print Bar (hidden in print) */}
        <div className="flex items-center justify-between pb-6 border-b border-border/80 print:hidden">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <ToggleRight className="size-4" />
            </div>
            <span className="font-bold text-sm tracking-tight">ScopeKeeper Official Change Order</span>
          </div>
          <Button size="sm" variant="outline" onClick={() => window.print()} className="gap-1.5 text-xs">
            <Printer className="size-3.5" />
            <span>Print / Save PDF</span>
          </Button>
        </div>

        {/* Change Order Header */}
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-primary/10 px-2 py-0.5 font-mono text-xs font-bold text-primary">
                {order.id}
              </span>
              <span className="text-xs text-muted-foreground uppercase tracking-widest font-semibold">
                Change Order Proposal
              </span>
            </div>
            <h1 className="mt-2 text-2xl font-bold text-foreground">{order.title}</h1>
            <p className="mt-1 text-xs text-muted-foreground">
              Statement of Work Addendum · Governed by ScopeKeeper Autonomous Client Desk
            </p>
          </div>

          <div className="text-left sm:text-right text-xs space-y-1">
            <div className="text-muted-foreground">Client: <strong className="text-foreground">{order.client}</strong></div>
            <div className="text-muted-foreground">Agency: <strong className="text-foreground">{order.agency}</strong></div>
            <div className="text-muted-foreground font-mono">Date: Nov 6, 2026</div>
          </div>
        </div>

        {/* Client Ask Quote & Contract Reference */}
        <div className="rounded-xl bg-secondary/40 p-4 border border-border/70 space-y-2">
          <div className="text-[11px] font-semibold text-muted-foreground uppercase">
            Client Request &amp; SOW Basis
          </div>
          <blockquote className="text-sm font-medium italic text-foreground leading-relaxed">
            “We would love an Android app for the board meeting.”
          </blockquote>
          <p className="text-xs text-muted-foreground pt-1 border-t border-border/40">
            <strong>Contract Basis:</strong> Excluded under SOW Exclusion 1.3 (Native mobile apps).
          </p>
        </div>

        {/* Standard Options */}
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wider">
            Pricing &amp; Delivery Options
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {order.options.map((opt) => {
              const isChosen = order.clientChoice === opt.key
              return (
                <div
                  key={opt.key}
                  className={`rounded-xl border p-4 flex flex-col justify-between space-y-3 ${
                    isChosen
                      ? 'border-primary bg-accent/30 ring-2 ring-primary'
                      : 'border-border bg-card'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="size-6 flex items-center justify-center rounded-md bg-secondary font-mono text-xs font-bold text-foreground">
                          {opt.key}
                        </span>
                        <span className="font-semibold text-sm">{opt.label}</span>
                      </div>
                      {isChosen && (
                        <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold text-primary-foreground">
                          Chosen
                        </span>
                      )}
                    </div>

                    <div className="mt-2 flex items-baseline gap-2">
                      <Money cents={opt.priceCents} className="text-2xl font-bold font-mono text-foreground" />
                      <span className="text-xs text-muted-foreground font-mono">
                        ({formatHours(opt.hours)})
                      </span>
                    </div>

                    <div className="text-xs font-medium text-amber-600 dark:text-amber-400 mt-1">
                      {opt.shiftDays > 0 ? `+${opt.shiftDays} days (Due ${opt.newDue})` : 'Zero date change'}
                    </div>

                    <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                      {opt.description}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Discord Response Prompt (§7: decisions stay in chat) */}
        <div className="rounded-xl border-2 border-primary/40 bg-accent/40 p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-start gap-3">
            <MessageSquare className="size-5 text-primary shrink-0 mt-0.5" />
            <div>
              <div className="font-bold text-sm text-foreground">How to Approve</div>
              <p className="text-xs text-muted-foreground mt-0.5">
                To confirm this change order, simply reply in <strong>#acme-client</strong> on Discord with:
              </p>
              <div className="mt-2 font-mono text-xs font-bold text-primary">
                A, B, C, or D
              </div>
            </div>
          </div>
          <span className="text-[11px] text-muted-foreground shrink-0 italic">
            Read-only document · Decisions stay in chat
          </span>
        </div>

        {/* Footer */}
        <div className="pt-6 border-t border-border/80 text-center text-xs text-muted-foreground space-y-1">
          <p>Pixel &amp; Co Client Services · Powered by Switch Protocol</p>
          <p className="font-mono text-[10px]">Reference: SOW-2026-ACME-001 · ScopeKeeper v1.0</p>
        </div>
      </div>
    </div>
  )
}
