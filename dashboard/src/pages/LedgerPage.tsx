import { useEffect, useState } from 'react'
import {
  Download,
  Lightbulb,
  Sparkles,
} from 'lucide-react'
import { Avatar } from '@/components/Avatar'
import { ChatLink } from '@/components/ChatLink'
import { DualTime } from '@/components/DualTime'
import { Money } from '@/components/Money'
import { SwitchTag } from '@/components/SwitchTag'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { LedgerEntry, Overview } from '@/lib/api/types'
import { formatHours } from '@/lib/format'
import { person } from '@/lib/people'
import { cn } from '@/lib/utils'

export function LedgerPage() {
  const [month, setMonth] = useState('2026-11')
  const [data, setData] = useState<{ overview: Overview; entries: LedgerEntry[] } | null>(null)
  const [renewals, setRenewals] = useState<
    { theme: string; askIds: string[]; hours: number; proposal: string }[]
  >([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetch(`/api/ledger?month=${month}`).then((r) => r.json()),
      fetch('/api/renewal').then((r) => r.json()),
    ])
      .then(([ledgerData, renewalData]) => {
        setData(ledgerData)
        setRenewals(renewalData)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [month])

  const handleDownloadCsv = () => {
    window.location.href = `/api/invoice?month=${month}`
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Scope Ledger &amp; Billing
            </h1>
            <SwitchTag kind="Reference" label="Reference · Ledger Summary" />
          </div>
          <p className="text-xs text-muted-foreground">
            Audit trail of revenue protected, approved change orders, goodwill allocations, and contract renewals.
          </p>
        </div>

        {/* Month Picker & Download CSV */}
        <div className="flex items-center gap-2">
          <select
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-semibold text-foreground focus:outline-hidden"
          >
            <option value="2026-11">November 2026</option>
            <option value="2026-10">October 2026</option>
          </select>

          <Button
            type="button"
            size="sm"
            variant="default"
            onClick={handleDownloadCsv}
            className="gap-1.5 text-xs font-semibold"
          >
            <Download className="size-3.5" />
            <span>Download Invoice CSV</span>
          </Button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      {loading || !data ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {/* Revenue Protected */}
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-xs font-medium text-muted-foreground">Revenue Protected This Month</div>
            <div className="mt-2 flex items-baseline gap-2">
              <Money cents={data.overview.revenueProtectedCents} className="font-mono text-3xl font-bold text-foreground" />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">Priced &amp; approved out-of-scope work</p>
          </div>

          {/* Change Orders Count */}
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-xs font-medium text-muted-foreground">Change Orders &amp; Swaps</div>
            <div className="mt-2 flex items-baseline gap-2 font-mono">
              <span className="text-2xl font-bold text-foreground">{data.overview.changeOrders.approved} approved</span>
              <span className="text-xs text-muted-foreground">· {data.overview.changeOrders.swaps} swaps</span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{data.overview.changeOrders.sent} total change orders proposed</p>
          </div>

          {/* Goodwill Bucket */}
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-xs font-medium text-muted-foreground">Goodwill Hours Allocated</div>
            <div className="mt-2 flex items-baseline gap-2 font-mono">
              <span className="text-2xl font-bold text-foreground">{data.overview.goodwill.usedHours} of {data.overview.goodwill.bucketHours} h</span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">Account manager goodwill grant limit</p>
          </div>
        </div>
      )}

      {/* Renewal Insights Cards (§8) */}
      {renewals.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
            <Lightbulb className="size-4 text-amber-500" />
            <span>Contract Renewal Insights</span>
          </h2>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {renewals.map((r, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-xs text-foreground"
              >
                <Sparkles className="size-4 text-amber-500 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="font-bold text-foreground">{r.theme} Add-On Proposal</div>
                  <p className="text-muted-foreground">{r.proposal}</p>
                  <div className="flex items-center gap-2 pt-1 font-mono text-[11px] text-muted-foreground">
                    <span>{r.hours} cumulative hours</span>
                    <span>·</span>
                    <span>Asks: {r.askIds.join(', ')}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Ledger Entries Table */}
      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
        <div className="p-4 border-b border-border/80 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">Ledger Transactions</h3>
          <span className="font-mono text-xs text-muted-foreground">{data?.entries.length ?? 0} entries</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <caption className="sr-only">Scopekeeper Billing &amp; Change Ledger Entries</caption>
            <thead>
              <tr className="border-b border-border bg-secondary/40 font-semibold text-muted-foreground">
                <th scope="col" className="px-4 py-3">Date</th>
                <th scope="col" className="px-4 py-3 font-mono">Reference</th>
                <th scope="col" className="px-4 py-3">Description</th>
                <th scope="col" className="px-4 py-3">Type</th>
                <th scope="col" className="px-4 py-3">Effort</th>
                <th scope="col" className="px-4 py-3 text-right">Amount</th>
                <th scope="col" className="px-4 py-3">Approver</th>
                <th scope="col" className="px-4 py-3 text-right">Chat Link</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {data?.entries.map((entry, idx) => {
                return (
                  <tr key={idx} className="hover:bg-secondary/30 transition-colors">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <DualTime iso={entry.date} className="text-xs" />
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold text-primary whitespace-nowrap">
                      {entry.ref}
                    </td>
                    <td className="px-4 py-3 font-medium text-foreground max-w-xs truncate">
                      {entry.title}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={cn(
                          'rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider',
                          entry.kind === 'change_order'
                            ? 'bg-primary/10 text-primary'
                            : entry.kind === 'swap'
                              ? 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-300'
                              : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
                        )}
                      >
                        {entry.kind.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-muted-foreground whitespace-nowrap">
                      {formatHours(entry.hours)}
                    </td>
                    <td className="px-4 py-3 font-mono font-bold text-foreground text-right whitespace-nowrap">
                      {entry.amountCents > 0 ? <Money cents={entry.amountCents} /> : '$0'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {entry.approvedBy ? (
                        <div className="flex items-center gap-1.5 font-medium text-foreground">
                          <Avatar id={entry.approvedBy} size="xs" />
                          <span>{person(entry.approvedBy).name}</span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground/60">--</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      {entry.link ? <ChatLink link={entry.link} variant="open" /> : '--'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
