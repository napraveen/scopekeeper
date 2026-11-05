import { useState } from 'react'
import { scaleTime } from 'd3-scale'
import { Clock } from 'lucide-react'
import { usePlan } from '@/lib/api/queries'
import type { Milestone, PlanItem } from '@/lib/api/types'
import { formatHours } from '@/lib/format'
import { cn } from '@/lib/utils'

export function PlanTimeline() {
  const { data: plan, isLoading } = usePlan()
  const [overlayOption, setOverlayOption] = useState<'NONE' | 'A' | 'C'>('NONE')

  if (isLoading || !plan) {
    return <div className="h-64 rounded-xl border border-border bg-card animate-pulse" />
  }

  // Date range for the timeline: Oct 12, 2026 to Jan 4, 2027
  const startDate = new Date('2026-10-12')
  const endDate = new Date('2027-01-04')
  const todayDate = new Date('2026-11-05T20:30:00') // Simulated story time

  const width = 900
  const height = 360
  const margin = { top: 40, right: 40, bottom: 40, left: 180 }
  const innerWidth = width - margin.left - margin.right

  const timeScale = scaleTime().domain([startDate, endDate]).range([0, innerWidth])

  // Weekly tick marks
  const weeks = [
    new Date('2026-10-12'),
    new Date('2026-10-19'),
    new Date('2026-10-26'),
    new Date('2026-11-02'),
    new Date('2026-11-09'),
    new Date('2026-11-16'),
    new Date('2026-11-23'),
    new Date('2026-11-30'),
    new Date('2026-12-07'),
    new Date('2026-12-14'),
    new Date('2026-12-21'),
    new Date('2026-12-28'),
  ]

  const todayX = timeScale(todayDate)

  // Ghost milestone position based on overlayOption
  const m2Due = new Date('2026-12-12')
  const ghostM2Due =
    overlayOption === 'A'
      ? new Date('2026-12-24')
      : overlayOption === 'C'
        ? new Date('2026-12-15')
        : null

  // Collect all items across milestones
  let rowIndex = 0
  const rows: { milestone: Milestone; item: PlanItem; row: number }[] = []
  for (const m of plan.milestones) {
    for (const item of m.items) {
      rows.push({ milestone: m, item, row: rowIndex++ })
    }
  }

  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-4 shadow-xs">
      {/* Controls & Legend */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-foreground">Delivery Timeline &amp; Milestones</h3>
            <span className="rounded bg-secondary px-2 py-0.5 font-mono text-xs text-muted-foreground">
              {plan.capacityHoursPerWeek} h/week capacity
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Weekly sprint allocation showing completed work, active deliverables, and scope swaps.
          </p>
        </div>

        {/* Overlay ghosts */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted-foreground font-medium">Ghost overlay:</span>
          <select
            value={overlayOption}
            onChange={(e) => setOverlayOption(e.target.value as 'NONE' | 'A' | 'C')}
            className="rounded-lg border border-border bg-background px-2.5 py-1 text-xs font-medium text-foreground focus:outline-hidden"
          >
            <option value="NONE">None (Baseline)</option>
            <option value="A">Overlay Option A (+12d)</option>
            <option value="C">Overlay Option C (+3d)</option>
          </select>
        </div>
      </div>

      {/* SVG Timeline */}
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full min-w-[750px] select-none text-xs" role="img">
          <g transform={`translate(${margin.left}, ${margin.top})`}>
            {/* Grid & Week headers */}
            {weeks.map((w, i) => {
              const x = timeScale(w)
              const label = `${w.toLocaleString('en-US', { month: 'short' })} ${w.getDate()}`
              return (
                <g key={i} transform={`translate(${x}, 0)`}>
                  <line y1={0} y2={height - margin.top - margin.bottom} className="stroke-border/50" strokeDasharray="2 2" />
                  <text y={-10} textAnchor="middle" className="fill-muted-foreground font-mono text-[10px]">
                    {label}
                  </text>
                </g>
              )
            })}

            {/* Today line */}
            <g transform={`translate(${todayX}, 0)`}>
              <line
                y1={-15}
                y2={height - margin.top - margin.bottom}
                className="stroke-amber-500"
                strokeWidth={2}
                strokeDasharray="4 2"
              />
              <rect x={-22} y={-26} width={44} height={16} rx={3} className="fill-amber-500" />
              <text y={-14} textAnchor="middle" className="fill-white font-mono font-bold text-[9px]">
                TODAY
              </text>
            </g>

            {/* Milestone M1 due marker */}
            <g transform={`translate(${timeScale(new Date('2026-10-25'))}, 0)`}>
              <line y1={0} y2={height - margin.top - margin.bottom} className="stroke-emerald-600/70" strokeWidth={1.5} />
              <circle cy={0} r={4} className="fill-emerald-600" />
              <text y={-5} textAnchor="middle" className="fill-emerald-600 dark:fill-emerald-400 font-bold text-[10px]">
                M1 Launch (Done)
              </text>
            </g>

            {/* Milestone M2 due marker */}
            <g transform={`translate(${timeScale(m2Due)}, 0)`}>
              <line y1={0} y2={height - margin.top - margin.bottom} className="stroke-primary" strokeWidth={2} />
              <circle cy={0} r={4} className="fill-primary" />
              <text y={-5} textAnchor="middle" className="fill-primary font-bold text-[10px]">
                M2 Due Dec 12
              </text>
            </g>

            {/* Ghost M2 due marker if overlay selected */}
            {ghostM2Due && (
              <g transform={`translate(${timeScale(ghostM2Due)}, 0)`}>
                <line
                  y1={0}
                  y2={height - margin.top - margin.bottom}
                  className="stroke-amber-500"
                  strokeWidth={2}
                  strokeDasharray="4 2"
                />
                <circle cy={0} r={4} className="fill-amber-500" />
                <text y={-5} textAnchor="middle" className="fill-amber-600 dark:fill-amber-400 font-bold text-[10px]">
                  {overlayOption === 'A' ? 'M2 Ghost Dec 24 (+12d)' : 'M2 Ghost Dec 15 (+3d)'}
                </text>
              </g>
            )}

            {/* Plan item bars */}
            {rows.map(({ item, row }) => {
              const rowY = row * 38 + 15

              // Approximate date span based on item
              let itemStart = new Date('2026-10-14')
              let itemEnd = new Date('2026-10-20')

              if (item.id === 'I1') {
                itemStart = new Date('2026-10-13')
                itemEnd = new Date('2026-10-20')
              } else if (item.id === 'I2') {
                itemStart = new Date('2026-10-18')
                itemEnd = new Date('2026-10-25')
              } else if (item.id === 'I8') {
                itemStart = new Date('2026-10-24')
                itemEnd = new Date('2026-10-28')
              } else if (item.id === 'I9') {
                itemStart = new Date('2026-11-10')
                itemEnd = new Date('2026-12-05')
              } else if (item.id === 'I10') {
                itemStart = new Date('2026-11-16')
                itemEnd = new Date('2026-12-01')
              } else if (item.id === 'I11') {
                itemStart = new Date('2026-11-10')
                itemEnd = new Date('2026-12-04')
              }

              const barX = timeScale(itemStart)
              const barWidth = Math.max(20, timeScale(itemEnd) - barX)
              const isSwapped = item.id === 'I11'

              return (
                <g key={item.id} transform={`translate(0, ${rowY})`}>
                  {/* Left Label */}
                  <text
                    x={-15}
                    y={14}
                    textAnchor="end"
                    className="fill-foreground font-medium text-[11px]"
                  >
                    {item.id}: {item.title}
                  </text>

                  {/* Bar */}
                  <rect
                    x={barX}
                    y={0}
                    width={barWidth}
                    height={20}
                    rx={5}
                    className={cn(
                      item.status === 'done'
                        ? 'fill-emerald-600/80'
                        : item.status === 'in_progress'
                          ? 'fill-primary'
                          : isSwapped
                            ? 'fill-indigo-600 stroke-2 stroke-amber-400'
                            : 'fill-secondary stroke-border stroke-1',
                    )}
                  />

                  {/* Hours inside bar */}
                  <text
                    x={barX + 8}
                    y={14}
                    className={cn(
                      'font-mono text-[10px] font-semibold',
                      item.status === 'done' || item.status === 'in_progress' || isSwapped
                        ? 'fill-white'
                        : 'fill-foreground',
                    )}
                  >
                    {formatHours(item.hours)}
                  </text>

                  {/* Swapped badge label if I11 */}
                  {isSwapped && (
                    <text
                      x={barX + barWidth + 8}
                      y={14}
                      className="fill-primary font-semibold text-[10px]"
                    >
                      ★ Swapped via CR-004, no date change
                    </text>
                  )}
                </g>
              )
            })}
          </g>
        </svg>
      </div>

      {/* Screen reader table fallback */}
      <table className="sr-only">
        <caption>Delivery Plan Items</caption>
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">Milestone</th>
            <th scope="col">Title</th>
            <th scope="col">Hours</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ milestone, item }) => (
            <tr key={item.id}>
              <td>{item.id}</td>
              <td>{milestone.name}</td>
              <td>{item.title}</td>
              <td>{item.hours}</td>
              <td>{item.status}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Legend */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/70 pt-3 text-xs text-muted-foreground">
        <div className="flex flex-wrap items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="size-3 rounded-xs bg-emerald-600" /> Completed
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-3 rounded-xs bg-primary" /> In Progress
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-3 rounded-xs bg-secondary border border-border" /> Unstarted
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-3 rounded-xs bg-indigo-600 border border-amber-400" /> Swapped Item (CR-004)
          </span>
        </div>

        <div className="flex items-center gap-1 font-mono text-[11px]">
          <Clock className="size-3.5 text-amber-500" />
          <span>Timeline synced to Switch execution events</span>
        </div>
      </div>
    </div>
  )
}
