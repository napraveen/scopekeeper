import { useState } from 'react'
import { useParams } from 'react-router'
import { Money } from '@/components/Money'
import { Skeleton } from '@/components/ui/skeleton'
import { useChangeRequests } from '@/lib/api/queries'
import { cn } from '@/lib/utils'
import { ChangeRequestDetail } from '@/features/change-requests/ChangeRequestDetail'

export function ChangeRequestsPage() {
  const { id: paramId } = useParams()
  const { data: changeRequests, isLoading } = useChangeRequests()

  const items = changeRequests ?? []

  // Default to paramId or CR-004 (hero change request) or the first one
  const [selectedId, setSelectedId] = useState<string>(
    paramId ?? 'CR-004',
  )

  const activeCr = items.find((c) => c.id === (paramId ?? selectedId)) ?? items[0]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Change Requests
            </h1>
            <span className="tabular rounded-full bg-secondary px-2 py-0.5 font-mono text-xs font-semibold text-muted-foreground">
              {items.length} total
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Out-of-scope work estimated from codebase git history, priced through rate-card envelopes.
          </p>
        </div>
      </div>

      {/* Change Requests Tabs / Selector Strip */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-18 rounded-xl" />
            ))
          : items.map((cr) => {
              const isSelected = activeCr?.id === cr.id
              const maxPrice = cr.options[0]?.priceCents ?? 0

              return (
                <button
                  key={cr.id}
                  type="button"
                  onClick={() => setSelectedId(cr.id)}
                  className={cn(
                    'flex flex-col justify-between rounded-xl border p-3 text-left transition-all',
                    isSelected
                      ? 'border-primary bg-accent/40 shadow-xs ring-1 ring-primary'
                      : 'border-border bg-card hover:bg-secondary/40',
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-foreground">
                      {cr.id}
                    </span>
                    <span className="rounded bg-secondary px-1.5 py-0.2 text-[10px] font-medium uppercase text-muted-foreground">
                      {cr.status.replace('_', ' ')}
                    </span>
                  </div>

                  <div className="mt-1 font-semibold text-xs text-foreground truncate">
                    {cr.title}
                  </div>

                  <div className="mt-2 flex items-baseline justify-between text-[11px]">
                    <span className="text-muted-foreground font-mono">
                      {cr.options.length} options
                    </span>
                    {maxPrice > 0 ? (
                      <Money cents={maxPrice} className="font-bold text-foreground" />
                    ) : (
                      <span className="font-mono text-muted-foreground">$0</span>
                    )}
                  </div>
                </button>
              )
            })}
      </div>

      {/* Active Change Request Detail */}
      {activeCr ? (
        <ChangeRequestDetail cr={activeCr} />
      ) : (
        <div className="rounded-xl border border-dashed border-border p-8 text-center text-xs text-muted-foreground">
          No change request selected.
        </div>
      )}
    </div>
  )
}
