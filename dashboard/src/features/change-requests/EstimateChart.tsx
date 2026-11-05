import { useId } from 'react'
import { scaleLinear } from 'd3-scale'
import { AlertTriangle, Code2, History } from 'lucide-react'
import type { Estimate } from '@/lib/api/types'
import { cn } from '@/lib/utils'

export function EstimateChart({
  estimate,
  className,
}: {
  estimate: Estimate
  className?: string
}) {
  const chartId = useId()
  const maxHours = 260
  const width = 640
  const height = 180
  const margin = { top: 30, right: 30, bottom: 40, left: 160 }

  const innerWidth = width - margin.left - margin.right
  const scale = scaleLinear().domain([0, maxHours]).range([0, innerWidth])

  const ticks = [0, 50, 100, 150, 200, 250]

  return (
    <div className={cn('rounded-xl border border-border bg-card p-5 space-y-5', className)}>
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-foreground">Codebase-Grounded Estimate</h3>
            <span className="rounded bg-secondary px-2 py-0.5 font-mono text-[11px] font-medium text-muted-foreground">
              Claude Code
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Estimated from commit history, touch files, and past merge trailers.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-medium">
          <span className="flex items-center gap-1 text-muted-foreground">
            <span className="size-2 rounded-full bg-primary" /> P50 (expected)
          </span>
          <span className="flex items-center gap-1 text-muted-foreground">
            <span className="h-2 w-4 rounded-xs bg-primary/30" /> P50–P90 range
          </span>
        </div>
      </div>

      {/* SVG Estimate Range Chart */}
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full min-w-[500px] text-xs select-none"
          role="img"
          aria-labelledby={`${chartId}-title`}
        >
          <title id={`${chartId}-title`}>
            Estimate range: Full Android app P50 190 h to P90 240 h; View-only version P50 56 h to P90 64 h.
          </title>

          {/* Grid lines */}
          <g transform={`translate(${margin.left}, ${margin.top})`}>
            {ticks.map((t) => (
              <g key={t} transform={`translate(${scale(t)}, 0)`}>
                <line y1={0} y2={height - margin.top - margin.bottom} className="stroke-border/70" strokeDasharray="3 3" />
                <text
                  y={height - margin.top - margin.bottom + 18}
                  textAnchor="middle"
                  className="fill-muted-foreground font-mono text-[10px]"
                >
                  {t} h
                </text>
              </g>
            ))}

            {/* Version 1: Full Android App */}
            <g transform="translate(0, 15)">
              <text x={-15} y={12} textAnchor="end" className="fill-foreground font-semibold text-xs">
                Full Android app
              </text>
              <text x={-15} y={26} textAnchor="end" className="fill-amber-600 dark:fill-amber-400 font-mono text-[10px]">
                (medium confidence)
              </text>

              {/* Range bar P50 to P90 */}
              <rect
                x={scale(estimate.full.p50Hours)}
                y={2}
                width={Math.max(4, scale(estimate.full.p90Hours) - scale(estimate.full.p50Hours))}
                height={16}
                rx={4}
                className="fill-primary/25 stroke-primary/50"
              />

              {/* Dot at P50 */}
              <circle
                cx={scale(estimate.full.p50Hours)}
                cy={10}
                r={6}
                className="fill-primary stroke-background"
                strokeWidth={2}
              />

              {/* P50 Label */}
              <text
                x={scale(estimate.full.p50Hours)}
                y={-4}
                textAnchor="middle"
                className="fill-primary font-mono font-bold text-[11px]"
              >
                190 h
              </text>

              {/* P90 Label */}
              <text
                x={scale(estimate.full.p90Hours)}
                y={-4}
                textAnchor="middle"
                className="fill-muted-foreground font-mono text-[10px]"
              >
                240 h
              </text>
            </g>

            {/* Version 2: Smaller View-Only Version */}
            {estimate.smaller && (
              <g transform="translate(0, 60)">
                <text x={-15} y={12} textAnchor="end" className="fill-foreground font-semibold text-xs">
                  View-only version
                </text>
                <text x={-15} y={26} textAnchor="end" className="fill-emerald-600 dark:fill-emerald-400 font-mono text-[10px]">
                  (high confidence)
                </text>

                {/* Range bar */}
                <rect
                  x={scale(estimate.smaller.p50Hours)}
                  y={2}
                  width={Math.max(4, scale(estimate.smaller.p90Hours) - scale(estimate.smaller.p50Hours))}
                  height={16}
                  rx={4}
                  className="fill-emerald-500/25 stroke-emerald-500/50"
                />

                {/* Dot at P50 */}
                <circle
                  cx={scale(estimate.smaller.p50Hours)}
                  cy={10}
                  r={6}
                  className="fill-emerald-600 dark:fill-emerald-400 stroke-background"
                  strokeWidth={2}
                />

                <text
                  x={scale(estimate.smaller.p50Hours)}
                  y={-4}
                  textAnchor="middle"
                  className="fill-emerald-600 dark:fill-emerald-400 font-mono font-bold text-[11px]"
                >
                  56 h
                </text>
              </g>
            )}

            {/* Similar past changes ticks on the same axis */}
            <g transform={`translate(0, ${height - margin.top - margin.bottom - 8})`}>
              {estimate.similar.map((sim, i) => (
                <g key={sim.ref} transform={`translate(${scale(sim.hours)}, 0)`}>
                  <line y1={-12} y2={0} className="stroke-primary/70" strokeWidth={1.5} />
                  <circle cy={0} r={3} className="fill-primary" />
                  <text
                    y={i % 2 === 0 ? -16 : -26}
                    textAnchor="middle"
                    className="fill-muted-foreground font-mono text-[9px]"
                  >
                    {sim.ref} ({sim.hours}h)
                  </text>
                </g>
              ))}
            </g>
          </g>
        </svg>
      </div>

      {/* Screen reader table fallback (§11) */}
      <table className="sr-only">
        <caption>Estimate breakdown for this change request</caption>
        <thead>
          <tr>
            <th scope="col">Scope version</th>
            <th scope="col">P50 hours</th>
            <th scope="col">P90 hours</th>
            <th scope="col">Confidence</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Full Android app</td>
            <td>{estimate.full.p50Hours}</td>
            <td>{estimate.full.p90Hours}</td>
            <td>{estimate.full.confidence}</td>
          </tr>
          {estimate.smaller && (
            <tr>
              <td>View-only version</td>
              <td>{estimate.smaller.p50Hours}</td>
              <td>{estimate.smaller.p90Hours}</td>
              <td>{estimate.smaller.confidence}</td>
            </tr>
          )}
        </tbody>
      </table>

      {/* Touches & Risks */}
      <div className="grid grid-cols-1 gap-4 border-t border-border/70 pt-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
            <Code2 className="size-3.5 text-primary" />
            <span>Files &amp; Components Touched</span>
          </div>
          <ul className="space-y-1">
            {estimate.touches.map((touch) => (
              <li key={touch} className="font-mono text-[11px] text-muted-foreground flex items-center gap-1">
                <span className="text-primary font-bold">›</span> {touch}
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
            <AlertTriangle className="size-3.5 text-amber-500" />
            <span>Identified Delivery Risks</span>
          </div>
          <ul className="space-y-1">
            {estimate.risks.map((risk) => (
              <li key={risk} className="text-[11px] text-muted-foreground flex items-start gap-1">
                <span className="text-amber-500 font-bold">•</span> {risk}
              </li>
            ))}
            {estimate.risks.length === 0 && (
              <li className="text-[11px] text-muted-foreground italic">No elevated delivery risks flagged.</li>
            )}
          </ul>
        </div>
      </div>

      {/* Codebase Grounding Citation */}
      <div className="flex items-center gap-2 rounded-lg bg-secondary/40 p-2.5 text-xs text-muted-foreground">
        <History className="size-4 text-primary shrink-0" />
        <span>
          Grounding: Estimate calibrated from <strong>41 repo commits</strong> and <strong>8 merge trailers</strong> with similar architectural complexity.
        </span>
      </div>
    </div>
  )
}
