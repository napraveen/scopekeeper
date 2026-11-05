import { ShieldCheck, FileCheck2, HeartHandshake, Timer, Layers } from 'lucide-react'
import { Money } from '@/components/Money'
import { Skeleton } from '@/components/ui/skeleton'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { CATEGORY, CATEGORY_ORDER } from '@/lib/categories'
import { formatHours } from '@/lib/format'
import { useOverview } from '@/lib/api/queries'
import { cn } from '@/lib/utils'

/**
 * KPI strip (FRONTEND_PROMPT §6):
 * 1. Revenue protected this month as a number ticker ($1,890 to $2,030 during the story)
 * 2. Change orders sent, approved, pending and swapped
 * 3. Goodwill as a small gauge (2 of 8 h)
 * 4. Median minutes from ask to decision
 * 5. Asks by category as a compact stacked bar (with text summary & screen-reader table fallback)
 */
export function KpiStrip() {
  const { data: overview, isLoading } = useOverview()

  if (isLoading || !overview) {
    return (
      <section aria-label="Monthly key metrics" className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </section>
    )
  }

  const { revenueProtectedCents, changeOrders, goodwill, medianAskToDecisionMinutes, asksByCategory } =
    overview

  const goodwillPct =
    goodwill.bucketHours > 0
      ? Math.min(100, Math.round((goodwill.usedHours / goodwill.bucketHours) * 100))
      : 0

  const totalCategorised = CATEGORY_ORDER.reduce((sum, key) => sum + (asksByCategory[key] ?? 0), 0)

  return (
    <section
      aria-label="Monthly key metrics"
      className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5"
    >
      {/* 1. Revenue protected */}
      <div className="flex flex-col justify-between rounded-xl border border-border bg-card p-4">
        <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
          <span>Revenue protected · Nov</span>
          <ShieldCheck className="size-4 text-primary" aria-hidden="true" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <Money
            cents={revenueProtectedCents}
            animate
            className="text-3xl font-semibold tracking-tight text-foreground"
          />
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          Approved out-of-scope work priced before build
        </p>
      </div>

      {/* 2. Change orders */}
      <div className="flex flex-col justify-between rounded-xl border border-border bg-card p-4">
        <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
          <span>Change orders</span>
          <FileCheck2 className="size-4 text-muted-foreground" aria-hidden="true" />
        </div>
        <dl className="mt-2 grid grid-cols-4 gap-2 text-center">
          <div className="rounded-lg bg-secondary/60 px-2 py-1.5">
            <dt className="text-[11px] text-muted-foreground">Sent</dt>
            <dd className="tabular text-base font-semibold text-foreground">{changeOrders.sent}</dd>
          </div>
          <div className="rounded-lg bg-secondary/60 px-2 py-1.5">
            <dt className="text-[11px] text-muted-foreground">Approved</dt>
            <dd className="tabular text-base font-semibold text-foreground">
              {changeOrders.approved}
            </dd>
          </div>
          <div className="rounded-lg bg-secondary/60 px-2 py-1.5">
            <dt className="text-[11px] text-muted-foreground">Pending</dt>
            <dd className="tabular text-base font-semibold text-foreground">
              {changeOrders.pending}
            </dd>
          </div>
          <div className="rounded-lg bg-secondary/60 px-2 py-1.5">
            <dt className="text-[11px] text-muted-foreground">Swaps</dt>
            <dd className="tabular text-base font-semibold text-primary">{changeOrders.swaps}</dd>
          </div>
        </dl>
      </div>

      {/* 3. Goodwill gauge */}
      <div className="flex flex-col justify-between rounded-xl border border-border bg-card p-4">
        <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
          <span>Goodwill bucket</span>
          <HeartHandshake className="size-4 text-muted-foreground" aria-hidden="true" />
        </div>
        <div className="mt-2 flex items-baseline justify-between">
          <span className="tabular text-xl font-semibold text-foreground">
            {formatHours(goodwill.usedHours, { unit: false })} of {formatHours(goodwill.bucketHours)}
          </span>
          <span className="tabular font-mono text-xs text-muted-foreground">
            {formatHours(Math.max(0, goodwill.bucketHours - goodwill.usedHours))} left
          </span>
        </div>
        <div
          role="meter"
          aria-label="Goodwill hours used this month"
          aria-valuemin={0}
          aria-valuemax={goodwill.bucketHours}
          aria-valuenow={goodwill.usedHours}
          aria-valuetext={`${goodwill.usedHours} of ${goodwill.bucketHours} hours used`}
          className="mt-2 h-2 w-full overflow-hidden rounded-full bg-secondary"
        >
          <div
            className="h-full rounded-full bg-primary transition-all duration-300"
            style={{ width: `${goodwillPct}%` }}
          />
        </div>
      </div>

      {/* 4. Median ask to decision */}
      <div className="flex flex-col justify-between rounded-xl border border-border bg-card p-4">
        <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
          <span>Median ask to decision</span>
          <Timer className="size-4 text-muted-foreground" aria-hidden="true" />
        </div>
        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="tabular text-3xl font-semibold tracking-tight text-foreground">
            {medianAskToDecisionMinutes}
          </span>
          <span className="text-sm font-medium text-muted-foreground">min</span>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          End-to-end across Mumbai and New York
        </p>
      </div>

      {/* 5. Asks by category stacked bar */}
      <div className="flex flex-col justify-between rounded-xl border border-border bg-card p-4 sm:col-span-2 xl:col-span-1">
        <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
          <span>Asks by category</span>
          <span className="tabular font-mono text-xs text-foreground">{totalCategorised} total</span>
        </div>

        {totalCategorised === 0 ? (
          <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
            <Layers className="size-3.5" aria-hidden="true" />
            <span>No sorted asks this month yet</span>
          </div>
        ) : (
          <>
            <div
              className="mt-2 flex h-2.5 w-full overflow-hidden rounded-full bg-secondary p-0.5 gap-0.5"
              aria-hidden="true"
            >
              {CATEGORY_ORDER.map((cat) => {
                const count = asksByCategory[cat] ?? 0
                if (count === 0) return null
                const meta = CATEGORY[cat]
                const pct = (count / totalCategorised) * 100
                return (
                  <Tooltip key={cat}>
                    <TooltipTrigger asChild>
                      <div
                        className={cn('h-full first:rounded-l-full last:rounded-r-full transition-all duration-300', meta.barClass)}
                        style={{ width: `${pct}%` }}
                      />
                    </TooltipTrigger>
                    <TooltipContent className="text-xs">
                      {meta.label}: {count}
                    </TooltipContent>
                  </Tooltip>
                )
              })}
            </div>

            <div className="mt-2 flex flex-wrap gap-x-2.5 gap-y-1">
              {CATEGORY_ORDER.map((cat) => {
                const count = asksByCategory[cat] ?? 0
                if (count === 0) return null
                const meta = CATEGORY[cat]
                const Icon = meta.icon
                return (
                  <span
                    key={cat}
                    className="inline-flex items-center gap-1 text-[11px] text-muted-foreground"
                  >
                    <Icon className="size-3 shrink-0" aria-hidden="true" />
                    <span>{meta.short}</span>
                    <span className="tabular font-mono font-semibold text-foreground">{count}</span>
                  </span>
                )
              })}
            </div>

            {/* Accessible table fallback for screen readers (§11) */}
            <table className="sr-only">
              <caption>Asks by category for November 2026</caption>
              <thead>
                <tr>
                  <th scope="col">Category</th>
                  <th scope="col">Count</th>
                </tr>
              </thead>
              <tbody>
                {CATEGORY_ORDER.map((cat) => (
                  <tr key={cat}>
                    <td>{CATEGORY[cat].label}</td>
                    <td>{asksByCategory[cat] ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </section>
  )
}
