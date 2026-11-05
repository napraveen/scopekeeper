import { Calendar } from 'lucide-react'
import type { OptionKey } from '@/lib/api/types'

export function WhatIfTimeline({
  hoveredOption,
  clientChoice,
}: {
  hoveredOption: OptionKey | null
  clientChoice?: OptionKey | 'DECLINE'
}) {
  const activeKey = hoveredOption ?? (clientChoice !== 'DECLINE' ? clientChoice : null)

  // Timeline baseline: Dec 12, 2026
  let ghostDue = '2026-12-12'
  let labelText = 'Milestone M2 Reporting release is due Dec 12, 2026.'
  let shiftDays = 0

  if (activeKey === 'A') {
    ghostDue = '2026-12-24'
    shiftDays = 12
    labelText = 'Option A adds 200 h of work: Milestone M2 moves from Dec 12 to Dec 24 (+12 days).'
  } else if (activeKey === 'B') {
    ghostDue = '2026-12-12'
    shiftDays = 0
    labelText = 'Option B schedules Android app for next phase: Milestone M2 stays Dec 12 (0 days shift).'
  } else if (activeKey === 'C') {
    ghostDue = '2026-12-15'
    shiftDays = 3
    labelText = 'Option C view-only board version: Milestone M2 moves 3 days to Dec 15.'
  } else if (activeKey === 'D') {
    ghostDue = '2026-12-12'
    shiftDays = 0
    labelText = 'Option D scope swap: Swaps out unstarted I9 (58h) for View-only Android (56h). No date change!'
  }

  // Calculate percentages along December (Dec 1 to Dec 31)
  const dec1 = new Date('2026-12-01').getTime()
  const dec31 = new Date('2026-12-31').getTime()
  const totalMs = dec31 - dec1

  const baselineMs = new Date('2026-12-12').getTime()
  const baselinePct = ((baselineMs - dec1) / totalMs) * 100

  const ghostMs = new Date(ghostDue).getTime()
  const ghostPct = ((ghostMs - dec1) / totalMs) * 100

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="size-4 text-primary" />
          <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider">
            What-If Milestone M2 Impact
          </h4>
        </div>
        {activeKey && (
          <span className="font-mono text-xs font-bold text-primary">
            Previewing Option {activeKey}
          </span>
        )}
      </div>

      <p className="text-xs text-muted-foreground">{labelText}</p>

      {/* Interactive timeline bar */}
      <div className="relative pt-6 pb-4">
        {/* Track for December */}
        <div className="relative h-2 w-full rounded-full bg-secondary overflow-visible">
          {/* Baseline marker: Dec 12 */}
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 flex flex-col items-center"
            style={{ left: `${baselinePct}%` }}
          >
            <div className="size-3.5 rounded-full bg-foreground border-2 border-background shadow-xs" />
            <span className="mt-1 font-mono text-[10px] font-semibold text-foreground whitespace-nowrap">
              Dec 12 (Base)
            </span>
          </div>

          {/* Ghost marker when shifted */}
          {shiftDays > 0 && (
            <>
              {/* Shift connector */}
              <div
                className="absolute top-0 h-full bg-amber-500/30 rounded-full"
                style={{
                  left: `${baselinePct}%`,
                  width: `${ghostPct - baselinePct}%`,
                }}
              />
              <div
                className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 flex flex-col items-center animate-in fade-in duration-200"
                style={{ left: `${ghostPct}%` }}
              >
                <div className="size-3.5 rounded-full bg-amber-500 border-2 border-background shadow-xs" />
                <span className="mt-1 font-mono text-[10px] font-bold text-amber-600 dark:text-amber-400 whitespace-nowrap">
                  Dec 24 (+12d)
                </span>
              </div>
            </>
          )}

          {activeKey === 'D' && (
            <div
              className="absolute -top-7 -translate-x-1/2 rounded bg-emerald-600 px-2 py-0.5 text-[10px] font-bold text-white shadow-xs"
              style={{ left: `${baselinePct}%` }}
            >
              ✓ Safe 0d Shift
            </div>
          )}
        </div>

        {/* Axis markers */}
        <div className="mt-6 flex justify-between text-[10px] font-mono text-muted-foreground border-t border-border/40 pt-1">
          <span>Dec 1</span>
          <span>Dec 8</span>
          <span>Dec 15</span>
          <span>Dec 22</span>
          <span>Dec 29</span>
        </div>
      </div>
    </div>
  )
}
