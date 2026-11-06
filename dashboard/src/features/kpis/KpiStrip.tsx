import { ShieldCheck, FileCheck2, HeartHandshake, Timer, Layers, CheckCircle2 } from 'lucide-react'
import { Money } from '@/components/Money'
import { Skeleton } from '@/components/ui/skeleton'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { CATEGORY, CATEGORY_ORDER } from '@/lib/categories'
import { formatHours } from '@/lib/format'
import { useOverview } from '@/lib/api/queries'
import { cn } from '@/lib/utils'

/**
 * KPI strip (FRONTEND_PROMPT §6, elevated with UI UX Pro Max design intelligence):
 * Executive command deck:
 * 1. Revenue protected ticker ($1,890 to $2,030) with ambient highlight
 * 2. Change orders breakdown with distinct status pills
 * 3. Goodwill bucket as an 8-segment battery meter (2 of 8 h)
 * 4. Median minutes with live status badge
 * 5. Stacked category bar with accessible screen-reader table
 */
export function KpiStrip() {
  const { data: overview, isLoading } = useOverview()

  if (isLoading || !overview) {
    return (
      <section aria-label="Monthly key metrics" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-32 rounded-2xl" />
        ))}
      </section>
    )
  }

  const { revenueProtectedCents, changeOrders, goodwill, medianAskToDecisionMinutes, asksByCategory } =
    overview

  const totalCategorised = CATEGORY_ORDER.reduce((sum, key) => sum + (asksByCategory[key] ?? 0), 0)

  // 8-segment battery gauge for the 8 hours goodwill bucket
  const totalBucketHours = goodwill.bucketHours || 8
  const usedHours = Math.min(totalBucketHours, Math.max(0, goodwill.usedHours))
  const remainingHours = Math.max(0, totalBucketHours - usedHours)

  return (
    <section
      aria-label="Monthly key metrics"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5"
    >
      {/* 1. Revenue Protected Card */}
      <div className="relative overflow-hidden flex flex-col justify-between rounded-2xl border border-border/80 glass-card p-5 hover-lift">
        <div className="absolute top-0 right-0 -mr-6 -mt-6 size-24 rounded-full bg-emerald-500/10 blur-xl pointer-events-none" />

        <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
          <span className="uppercase tracking-wider text-[11px]">Revenue Protected</span>
          <div className="flex size-7 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <ShieldCheck className="size-4" aria-hidden="true" />
          </div>
        </div>

        <div className="mt-3 flex items-baseline gap-2">
          <Money
            cents={revenueProtectedCents}
            animate
            className="text-3xl font-extrabold tracking-tight text-foreground font-mono"
          />
        </div>

        <div className="mt-2.5 flex items-center gap-1.5 pt-2 border-t border-border/60 text-xs">
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-700 dark:text-emerald-300">
            <CheckCircle2 className="size-3" /> Nov 2026
          </span>
          <span className="text-[11px] text-muted-foreground truncate">
            Priced before build
          </span>
        </div>
      </div>

      {/* 2. Change Orders Breakdown */}
      <div className="flex flex-col justify-between rounded-2xl border border-border/80 glass-card p-5 hover-lift">
        <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
          <span className="uppercase tracking-wider text-[11px]">Change Orders</span>
          <div className="flex size-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <FileCheck2 className="size-4" aria-hidden="true" />
          </div>
        </div>

        <dl className="mt-3 grid grid-cols-4 gap-1.5 text-center">
          <div className="rounded-xl bg-secondary/50 p-1.5 border border-border/50">
            <dt className="text-[10px] uppercase font-semibold text-muted-foreground">Sent</dt>
            <dd className="tabular text-base font-bold text-foreground mt-0.5">{changeOrders.sent}</dd>
          </div>
          <div className="rounded-xl bg-secondary/50 p-1.5 border border-border/50">
            <dt className="text-[10px] uppercase font-semibold text-muted-foreground">Approved</dt>
            <dd className="tabular text-base font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
              {changeOrders.approved}
            </dd>
          </div>
          <div className="rounded-xl bg-secondary/50 p-1.5 border border-border/50">
            <dt className="text-[10px] uppercase font-semibold text-muted-foreground">Pending</dt>
            <dd className="tabular text-base font-bold text-foreground mt-0.5">
              {changeOrders.pending}
            </dd>
          </div>
          <div className={cn(
            'rounded-xl p-1.5 border transition-colors',
            changeOrders.swaps > 0
              ? 'bg-primary/15 border-primary/40 text-primary'
              : 'bg-secondary/50 border-border/50 text-foreground',
          )}>
            <dt className="text-[10px] uppercase font-semibold text-muted-foreground">Swaps</dt>
            <dd className="tabular text-base font-bold text-primary mt-0.5">{changeOrders.swaps}</dd>
          </div>
        </dl>

        <div className="mt-2.5 pt-2 border-t border-border/60 text-[11px] text-muted-foreground flex items-center justify-between">
          <span>CR-002 to CR-005</span>
          {changeOrders.swaps > 0 && (
            <span className="font-mono text-[10px] font-bold text-primary">1 Scope Swap ($0)</span>
          )}
        </div>
      </div>

      {/* 3. Goodwill Bucket - 8-Segment Battery Meter */}
      <div className="flex flex-col justify-between rounded-2xl border border-border/80 glass-card p-5 hover-lift">
        <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
          <span className="uppercase tracking-wider text-[11px]">Goodwill Bucket</span>
          <div className="flex size-7 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
            <HeartHandshake className="size-4" aria-hidden="true" />
          </div>
        </div>

        <div className="mt-3 flex items-baseline justify-between">
          <span className="tabular text-xl font-extrabold text-foreground">
            {formatHours(usedHours, { unit: false })} <span className="text-xs font-normal text-muted-foreground">of</span> {formatHours(totalBucketHours)}
          </span>
          <span className="tabular font-mono text-xs font-bold text-amber-700 dark:text-amber-300">
            {formatHours(remainingHours)} left
          </span>
        </div>

        {/* Tactile 8-Segment Meter */}
        <div
          role="meter"
          aria-label="Goodwill hours used this month"
          aria-valuemin={0}
          aria-valuemax={totalBucketHours}
          aria-valuenow={usedHours}
          aria-valuetext={`${usedHours} of ${totalBucketHours} hours used`}
          className="mt-2.5 flex items-center gap-1 w-full"
        >
          {Array.from({ length: 8 }).map((_, idx) => {
            const isFilled = idx < Math.round(usedHours)
            return (
              <div
                key={idx}
                className={cn(
                  'h-2.5 flex-1 rounded-sm transition-all duration-300',
                  isFilled
                    ? 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]'
                    : 'bg-secondary/80 border border-border/40',
                )}
                title={`Hour ${idx + 1}: ${isFilled ? 'Used' : 'Available'}`}
              />
            )
          })}
        </div>

        <div className="mt-2.5 pt-2 border-t border-border/60 text-[11px] text-muted-foreground">
          Monthly account manager leeway
        </div>
      </div>

      {/* 4. Median Ask to Decision */}
      <div className="flex flex-col justify-between rounded-2xl border border-border/80 glass-card p-5 hover-lift">
        <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
          <span className="uppercase tracking-wider text-[11px]">Median Decision</span>
          <div className="flex size-7 items-center justify-center rounded-lg bg-indigo-500/10 text-primary">
            <Timer className="size-4" aria-hidden="true" />
          </div>
        </div>

        <div className="mt-3 flex items-baseline gap-2">
          <span className="tabular text-3xl font-extrabold tracking-tight text-foreground font-mono">
            {medianAskToDecisionMinutes}
          </span>
          <span className="text-sm font-semibold text-muted-foreground">minutes</span>
        </div>

        <div className="mt-2.5 flex items-center justify-between pt-2 border-t border-border/60 text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1 font-semibold text-emerald-700 dark:text-emerald-400">
            <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Fast triage (&lt;1h)
          </span>
          <span className="font-mono text-[10px]">Mumbai · NY</span>
        </div>
      </div>

      {/* 5. Asks by Category Stacked Bar */}
      <div className="flex flex-col justify-between rounded-2xl border border-border/80 glass-card p-5 hover-lift sm:col-span-2 xl:col-span-1">
        <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
          <span className="uppercase tracking-wider text-[11px]">Asks by Category</span>
          <span className="tabular font-mono text-xs font-bold text-foreground bg-secondary px-2 py-0.5 rounded-full">
            {totalCategorised} total
          </span>
        </div>

        {totalCategorised === 0 ? (
          <div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
            <Layers className="size-3.5" aria-hidden="true" />
            <span>No sorted asks this month yet</span>
          </div>
        ) : (
          <>
            <div
              className="mt-3 flex h-3 w-full overflow-hidden rounded-full bg-secondary p-0.5 gap-0.5 shadow-2xs"
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

            <div className="mt-2 flex flex-wrap gap-x-2 gap-y-1">
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
                    <span className="tabular font-mono font-bold text-foreground">{count}</span>
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
