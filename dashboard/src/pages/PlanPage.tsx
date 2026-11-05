import { Sparkles } from 'lucide-react'
import { SwitchTag } from '@/components/SwitchTag'
import { usePlan } from '@/lib/api/queries'
import type { Milestone, PlanItem } from '@/lib/api/types'
import { PlanTimeline } from '@/features/plan/PlanTimeline'

export function PlanPage() {
  const { data: plan } = usePlan()

  const hasSwap = plan?.milestones.some((m: Milestone) => m.items.some((i: PlanItem) => i.id === 'I11'))

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Delivery Plan</h1>
            <SwitchTag kind="Reference" label="Reference · Delivery Plan" />
          </div>
          <p className="text-xs text-muted-foreground">
            Capacity-governed delivery timeline, milestone tracking, and autonomous scope swaps.
          </p>
        </div>

        {hasSwap && (
          <div className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-accent px-3 py-1 text-xs font-semibold text-accent-foreground">
            <Sparkles className="size-3.5 text-primary" />
            <span>Scope swap active: I9 swapped for I11 ($0, 0d shift)</span>
          </div>
        )}
      </div>

      {/* Main SVG Timeline Component */}
      <PlanTimeline />

      {/* Milestones Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {plan?.milestones.map((m: Milestone) => {
          const isDone = m.id === 'M1'
          const totalHours = m.items.reduce((s: number, i: PlanItem) => s + i.hours, 0)
          const doneHours = m.items.filter((i: PlanItem) => i.status === 'done').reduce((s: number, i: PlanItem) => s + i.hours, 0)

          return (
            <div
              key={m.id}
              className="rounded-xl border border-border bg-card p-4 space-y-3 shadow-xs"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-foreground">{m.id}</span>
                  <span className="font-semibold text-sm text-foreground">{m.name}</span>
                </div>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    isDone
                      ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                      : 'bg-primary/10 text-primary'
                  }`}
                >
                  {isDone ? 'Completed' : `Due ${m.due}`}
                </span>
              </div>

              <div className="flex justify-between text-xs text-muted-foreground font-mono">
                <span>Progress: {doneHours} of {totalHours} h</span>
                <span>{Math.round((doneHours / totalHours) * 100)}%</span>
              </div>

              <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                <div
                  className={`h-full ${isDone ? 'bg-emerald-600' : 'bg-primary'} rounded-full`}
                  style={{ width: `${Math.round((doneHours / totalHours) * 100)}%` }}
                />
              </div>

              <ul className="space-y-1.5 pt-1 divide-y divide-border/40">
                {m.items.map((item: PlanItem) => (
                  <li key={item.id} className="pt-1.5 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] font-semibold text-muted-foreground">
                        {item.id}
                      </span>
                      <span className="text-foreground font-medium">{item.title}</span>
                    </div>
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {item.hours} h
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </div>
  )
}
