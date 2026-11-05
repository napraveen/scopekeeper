import { ArrowRight, ArrowRightLeft, Check, CheckCircle2, XCircle } from 'lucide-react'
import { Money } from '@/components/Money'
import type { OptionKey, OptionQuote } from '@/lib/api/types'
import { formatHours } from '@/lib/format'
import { cn } from '@/lib/utils'

export function OptionsCards({
  options,
  clientChoice,
  selectedKeys,
  onToggleSelect,
  onHoverOption,
}: {
  options: OptionQuote[]
  clientChoice?: OptionKey | 'DECLINE'
  selectedKeys: OptionKey[]
  onToggleSelect?: (key: OptionKey) => void
  onHoverOption?: (key: OptionKey | null) => void
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Standardized Client Options</h3>
        <span className="text-xs text-muted-foreground">
          Hover any option to preview milestone impact below
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {options.map((opt) => {
          const isChosen = clientChoice === opt.key
          const isOtherChosen = Boolean(clientChoice && !isChosen)
          const isChecked = selectedKeys.includes(opt.key)
          const isDraft = opt.draft

          return (
            <div
              key={opt.key}
              onMouseEnter={() => onHoverOption?.(opt.key)}
              onMouseLeave={() => onHoverOption?.(null)}
              onFocus={() => onHoverOption?.(opt.key)}
              onBlur={() => onHoverOption?.(null)}
              tabIndex={0}
              className={cn(
                'group relative flex flex-col justify-between rounded-xl border p-4 transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-primary',
                isChosen
                  ? 'border-primary bg-accent/30 shadow-md ring-2 ring-primary/60'
                  : isOtherChosen
                    ? 'border-border/60 bg-card/40 opacity-50'
                    : 'border-border bg-card hover:border-primary/50 hover:bg-accent/15 hover:shadow-xs',
              )}
            >
              <div>
                {/* Header: Option Key & Selection */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="flex size-6 items-center justify-center rounded-md bg-secondary font-mono text-xs font-bold text-foreground">
                      {opt.key}
                    </span>
                    <span className="font-semibold text-sm text-foreground">{opt.label}</span>
                  </div>

                  {isChosen ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-primary px-2 py-0.5 font-mono text-[10px] font-bold text-primary-foreground shadow-xs">
                      <Check className="size-3" /> Chosen
                    </span>
                  ) : onToggleSelect ? (
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => onToggleSelect(opt.key)}
                      aria-label={`Select Option ${opt.key} for approval`}
                      className="size-4 rounded border-border text-primary focus:ring-primary"
                    />
                  ) : null}
                </div>

                {/* Price */}
                <div className="mt-3 flex items-baseline gap-2">
                  <Money
                    cents={opt.priceCents}
                    className="font-mono text-2xl font-bold tracking-tight text-foreground"
                  />
                  <span className="text-xs font-medium text-muted-foreground">
                    / {formatHours(opt.hours)}
                  </span>
                </div>

                {/* Date effect */}
                <div className="mt-1 flex items-center gap-1 text-xs font-medium">
                  {opt.shiftDays > 0 ? (
                    <span className="text-amber-600 dark:text-amber-400">
                      +{opt.shiftDays} days (M2 due {opt.newDue})
                    </span>
                  ) : (
                    <span className="text-emerald-600 dark:text-emerald-400">
                      No milestone date change
                    </span>
                  )}
                </div>

                {/* Description */}
                <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                  {opt.description}
                </p>

                {/* Card D Scope Swap Equal-Height Bars Visualization (§7) */}
                {opt.swapIn && opt.swapOut && (
                  <div className="mt-3 space-y-1.5 rounded-lg border border-border/70 bg-secondary/30 p-2.5">
                    <div className="flex items-center justify-between text-[11px] font-semibold text-foreground">
                      <span className="flex items-center gap-1">
                        <ArrowRightLeft className="size-3 text-primary" /> Scope Swap ($0)
                      </span>
                      <span className="font-mono text-[10px] text-emerald-600 dark:text-emerald-400">
                        Zero impact
                      </span>
                    </div>

                    {/* Out item */}
                    <div className="flex items-center justify-between rounded bg-card/80 px-2 py-1 text-[11px] border border-border/50">
                      <span className="text-muted-foreground line-through truncate max-w-[150px]">
                        I9 Admin analytics
                      </span>
                      <span className="font-mono text-muted-foreground line-through">58 h</span>
                    </div>

                    <div className="flex justify-center -my-1">
                      <ArrowRight className="size-3 rotate-90 text-primary" />
                    </div>

                    {/* In item */}
                    <div className="flex items-center justify-between rounded bg-accent/80 px-2 py-1 text-[11px] font-medium text-accent-foreground border border-primary/30">
                      <span className="truncate max-w-[150px]">View-only Android app</span>
                      <span className="font-mono font-bold text-primary">56 h</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Envelope status tags */}
              <div className="mt-4 pt-3 border-t border-border/60">
                {opt.priceCents <= 50000 && opt.shiftDays === 0 ? (
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="size-3" /> Inside auto-envelope
                  </span>
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {opt.priceCents > 50000 && (
                      <span className="inline-flex items-center gap-0.5 rounded bg-amber-500/10 px-1.5 py-0.2 text-[10px] font-medium text-amber-700 dark:text-amber-300">
                        <XCircle className="size-2.5" /> Over $500
                      </span>
                    )}
                    {opt.shiftDays > 0 && (
                      <span className="inline-flex items-center gap-0.5 rounded bg-amber-500/10 px-1.5 py-0.2 text-[10px] font-medium text-amber-700 dark:text-amber-300">
                        <XCircle className="size-2.5" /> Moves M2
                      </span>
                    )}
                  </div>
                )}
                {isDraft && (
                  <span className="mt-1 block text-[10px] text-muted-foreground italic">
                    Draft awaiting delivery lead confirmation
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
