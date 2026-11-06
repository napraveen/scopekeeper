import { ArrowRight, ArrowRightLeft, Check, CheckCircle2, Sparkles, XCircle } from 'lucide-react'
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
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-base font-bold tracking-tight text-foreground">Standardized Client Options</h3>
          <p className="text-xs text-muted-foreground">
            Deterministic options generated from real codebase history. Hover any card to preview milestone impact below.
          </p>
        </div>
        <span className="text-xs font-semibold text-primary">
          4 Options (A · B · C · D)
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {options.map((opt) => {
          const isChosen = clientChoice === opt.key
          const isOtherChosen = Boolean(clientChoice && !isChosen)
          const isChecked = selectedKeys.includes(opt.key)
          const isDraft = opt.draft
          const isSwapD = opt.key === 'D'

          return (
            <div
              key={opt.key}
              onMouseEnter={() => onHoverOption?.(opt.key)}
              onMouseLeave={() => onHoverOption?.(null)}
              onFocus={() => onHoverOption?.(opt.key)}
              onBlur={() => onHoverOption?.(null)}
              tabIndex={0}
              className={cn(
                'group relative flex flex-col justify-between rounded-2xl border p-5 transition-all duration-300 outline-none focus-visible:ring-2 focus-visible:ring-primary',
                isChosen
                  ? 'border-primary bg-primary/10 shadow-lg ring-2 ring-primary/60 scale-[1.02]'
                  : isOtherChosen
                    ? 'border-border/50 bg-card/40 opacity-45'
                    : isSwapD
                      ? 'border-emerald-500/50 bg-emerald-500/5 shadow-[0_4px_25px_rgba(16,185,129,0.1)] hover:border-emerald-500 hover:shadow-lg'
                      : 'border-border/80 glass-card hover:border-primary/50 hover:shadow-md hover:-translate-y-1',
              )}
            >
              <div>
                {/* Header: Option Key, Recommended Badge & Selection */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      'flex size-7 items-center justify-center rounded-lg font-mono text-xs font-black shadow-2xs',
                      isSwapD
                        ? 'bg-emerald-500 text-white'
                        : isChosen
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-secondary text-foreground',
                    )}>
                      {opt.key}
                    </span>
                    <span className="font-bold text-sm text-foreground">{opt.label}</span>
                  </div>

                  {isChosen ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-primary px-2.5 py-0.5 font-mono text-[10px] font-bold text-primary-foreground shadow-sm">
                      <Check className="size-3" /> Chosen
                    </span>
                  ) : isSwapD ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/40 px-2 py-0.5 font-mono text-[10px] font-bold text-emerald-700 dark:text-emerald-300">
                      <Sparkles className="size-3" /> Recommended
                    </span>
                  ) : onToggleSelect ? (
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => onToggleSelect(opt.key)}
                      aria-label={`Select Option ${opt.key} for approval`}
                      className="size-4 rounded border-border text-primary focus:ring-primary cursor-pointer"
                    />
                  ) : null}
                </div>

                {/* Price Display */}
                <div className="mt-3.5 flex items-baseline gap-2">
                  <Money
                    cents={opt.priceCents}
                    className={cn(
                      'font-mono text-2xl sm:text-3xl font-extrabold tracking-tight',
                      isSwapD ? 'text-emerald-600 dark:text-emerald-400' : 'text-foreground',
                    )}
                  />
                  <span className="text-xs font-semibold text-muted-foreground">
                    / {formatHours(opt.hours)}
                  </span>
                </div>

                {/* Milestone Delivery Effect */}
                <div className="mt-1.5 flex items-center gap-1 text-xs font-semibold">
                  {opt.shiftDays > 0 ? (
                    <span className="text-amber-700 dark:text-amber-300">
                      +{opt.shiftDays} days (M2 due {opt.newDue})
                    </span>
                  ) : (
                    <span className="text-emerald-700 dark:text-emerald-300">
                      ✓ No milestone date change
                    </span>
                  )}
                </div>

                {/* Description */}
                <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                  {opt.description}
                </p>

                {/* Card D Scope Swap Equal-Height Bars Visualization (§7) */}
                {opt.swapIn && opt.swapOut && (
                  <div className="mt-3.5 space-y-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3">
                    <div className="flex items-center justify-between text-[11px] font-bold text-foreground">
                      <span className="flex items-center gap-1 text-emerald-700 dark:text-emerald-300">
                        <ArrowRightLeft className="size-3.5" /> Scope Swap ($0)
                      </span>
                      <span className="font-mono text-[10px] font-extrabold text-emerald-700 dark:text-emerald-300 bg-emerald-500/20 px-1.5 py-0.2 rounded">
                        Zero impact
                      </span>
                    </div>

                    {/* Out item */}
                    <div className="flex items-center justify-between rounded-lg bg-card/90 px-2.5 py-1.5 text-xs border border-border/60">
                      <span className="text-muted-foreground line-through truncate max-w-[140px] font-medium">
                        I9 Admin analytics
                      </span>
                      <span className="font-mono text-muted-foreground line-through font-semibold">58 h</span>
                    </div>

                    <div className="flex justify-center -my-1">
                      <ArrowRight className="size-3.5 rotate-90 text-emerald-600 dark:text-emerald-400" />
                    </div>

                    {/* In item */}
                    <div className="flex items-center justify-between rounded-lg bg-emerald-500/20 px-2.5 py-1.5 text-xs font-bold text-foreground border border-emerald-500/40">
                      <span className="truncate max-w-[140px]">View-only Android app</span>
                      <span className="font-mono font-black text-emerald-700 dark:text-emerald-300">56 h</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Envelope status tags */}
              <div className="mt-4 pt-3 border-t border-border/60">
                {opt.priceCents <= 50000 && opt.shiftDays === 0 ? (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 dark:text-emerald-300">
                    <CheckCircle2 className="size-3.5" /> Inside auto-envelope
                  </span>
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {opt.priceCents > 50000 && (
                      <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 dark:text-amber-300">
                        <XCircle className="size-3" /> Over $500
                      </span>
                    )}
                    {opt.shiftDays > 0 && (
                      <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 dark:text-amber-300">
                        <XCircle className="size-3" /> Moves M2
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
