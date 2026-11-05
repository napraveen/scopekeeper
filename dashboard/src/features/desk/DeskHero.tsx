import { ArrowRightLeft, Moon, Sun } from 'lucide-react'
import { Avatar } from '@/components/Avatar'
import { SwitchTag } from '@/components/SwitchTag'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useNow } from '@/lib/clock'
import { demo, useDemoStore } from '@/lib/demo'
import { formatCountdown, formatDual } from '@/lib/format'
import { person } from '@/lib/people'
import { useDesk } from '@/lib/api/queries'
import { cn } from '@/lib/utils'

/**
 * The Desk hero (FRONTEND_PROMPT §6):
 * Large SVG toggle switch with Priya's avatar on the day side and Scout's on the night side,
 * the knob resting on the current holder. Beside it: holder name, mode (copilot by day,
 * autopilot by night), "until 9:30 AM IST · 11:00 PM ET", and a countdown.
 * In demo mode, shows a "Flip now" button.
 */
export function DeskHero() {
  const { data: desk, isLoading } = useDesk()
  const now = useNow()
  const demoAvailable = useDemoStore((s) => s.available)

  if (isLoading || !desk) {
    return (
      <section
        aria-label="Client desk status"
        className="rounded-xl border border-border bg-card p-5"
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <Skeleton className="h-20 w-full max-w-md rounded-xl" />
          <Skeleton className="h-14 w-64 rounded-lg" />
        </div>
      </section>
    )
  }

  const isScout = desk.holder === 'scout'
  const holder = person(desk.holder)
  const nextHolder = person(desk.nextHolder)
  const remainingMs = new Date(desk.nextHandoverAt).getTime() - now
  const countdown = formatCountdown(remainingMs)
  const untilDual = formatDual(desk.nextHandoverAt)

  const handleFlip = () => {
    if (demoAvailable) {
      demo().flipNow()
    }
  }

  return (
    <section
      aria-label="Client desk status"
      data-holder={desk.holder}
      data-mode={desk.mode}
      className="relative overflow-hidden rounded-xl border border-border bg-card p-4 sm:p-5"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        {/* Left: SVG toggle switch with Priya (Day) and Scout (Night) */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3">
            {/* Day side: Priya */}
            <div
              className={cn(
                'flex items-center gap-2 rounded-lg px-2.5 py-1.5 transition-opacity',
                !isScout ? 'opacity-100' : 'opacity-55',
              )}
            >
              <Avatar id="priya" size="md" />
              <div className="hidden sm:block">
                <div className="flex items-center gap-1 text-xs font-semibold text-foreground">
                  <Sun className="size-3.5 text-day" aria-hidden="true" />
                  <span>Priya</span>
                </div>
                <div className="text-[11px] text-muted-foreground">Day · Copilot</div>
              </div>
            </div>

            {/* Large SVG toggle switch */}
            <button
              type="button"
              role="switch"
              aria-checked={isScout}
              aria-label={`Client desk holder: ${holder.name} (${desk.mode} mode). Click to flip desk in demo mode.`}
              onClick={handleFlip}
              disabled={!demoAvailable}
              className={cn(
                'group relative inline-flex items-center rounded-full focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring',
                demoAvailable ? 'cursor-pointer' : 'cursor-default',
              )}
            >
              <svg
                width="148"
                height="56"
                viewBox="0 0 148 56"
                aria-hidden="true"
                className="overflow-visible select-none"
              >
                {/* Track */}
                <rect
                  x="2"
                  y="2"
                  width="144"
                  height="52"
                  rx="26"
                  className={cn(
                    ' transition-colors duration-300',
                    isScout
                      ? 'fill-indigo-950/90 stroke-indigo-500/40'
                      : 'fill-amber-500/15 stroke-amber-500/40',
                  )}
                  strokeWidth="1.5"
                />

                {/* Subtle horizon track markings */}
                <g
                  className={cn(
                    'transition-opacity duration-300',
                    isScout ? 'opacity-35' : 'opacity-80',
                  )}
                >
                  <circle cx="32" cy="28" r="10" className="fill-amber-500/20" />
                  <circle cx="32" cy="28" r="4.5" className="fill-amber-500" />
                </g>

                <g
                  className={cn(
                    'transition-opacity duration-300',
                    isScout ? 'opacity-90' : 'opacity-35',
                  )}
                >
                  <circle cx="116" cy="28" r="10" className="fill-indigo-400/20" />
                  <path
                    d="M119 22.5a6.5 6.5 0 1 0 0 11 5.5 5.5 0 0 1 0-11Z"
                    className="fill-indigo-300"
                  />
                  <circle cx="105" cy="20" r="1" className="fill-indigo-200" />
                  <circle cx="125" cy="19" r="1.2" className="fill-indigo-200" />
                </g>

                {/* Sliding Knob */}
                <g
                  style={{
                    transform: isScout ? 'translateX(88px)' : 'translateX(0px)',
                    transition: 'transform 300ms cubic-bezier(0.22, 1, 0.36, 1)',
                  }}
                >
                  <circle
                    cx="30"
                    cy="28"
                    r="21"
                    className={cn(
                      'transition-colors duration-300',
                      isScout
                        ? 'fill-indigo-500 stroke-indigo-300'
                        : 'fill-white stroke-amber-500/60 dark:fill-zinc-900',
                    )}
                    strokeWidth="1.5"
                  />
                  <text
                    x="30"
                    y="32"
                    textAnchor="middle"
                    className={cn(
                      'font-mono text-xs font-bold',
                      isScout ? 'fill-white' : 'fill-zinc-900 dark:fill-zinc-100',
                    )}
                  >
                    {isScout ? 'Sc' : 'P'}
                  </text>
                </g>
              </svg>
            </button>

            {/* Night side: Scout */}
            <div
              className={cn(
                'flex items-center gap-2 rounded-lg px-2.5 py-1.5 transition-opacity',
                isScout ? 'opacity-100' : 'opacity-55',
              )}
            >
              <Avatar id="scout" size="md" showVendor />
              <div className="hidden sm:block">
                <div className="flex items-center gap-1 text-xs font-semibold text-foreground">
                  <Moon className="size-3.5 text-night" aria-hidden="true" />
                  <span>Scout</span>
                </div>
                <div className="text-[11px] text-muted-foreground">Night · Autopilot</div>
              </div>
            </div>
          </div>

          {/* Holder status sentence */}
          <div className="space-y-1 border-t border-border pt-3 sm:border-t-0 sm:border-l sm:pt-0 sm:pl-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-medium text-muted-foreground">
                @client-desk
              </span>
              <SwitchTag kind="Role" label="Role · @client-desk" />
              {isScout && <SwitchTag kind="Agent · OpenCode" />}
              <span
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset',
                  isScout
                    ? 'bg-accent text-accent-foreground ring-primary/30'
                    : 'bg-amber-500/15 text-amber-800 ring-amber-500/30 dark:text-amber-200',
                )}
              >
                {isScout ? (
                  <Moon className="size-3" aria-hidden="true" />
                ) : (
                  <Sun className="size-3" aria-hidden="true" />
                )}
                <span>
                  {holder.name} · {desk.mode}
                </span>
              </span>
            </div>

            <p className="text-base font-semibold tracking-tight text-foreground sm:text-xl">
              {isScout
                ? 'Scout holds the client desk on autopilot'
                : 'Priya holds the client desk in copilot mode'}
            </p>

            <p className="tabular text-xs text-muted-foreground">
              Until <span className="font-medium text-foreground">{untilDual}</span> · Handover to{' '}
              <span className="font-medium text-foreground">{nextHolder.name}</span> in{' '}
              <span className="font-mono font-semibold text-foreground">{countdown}</span>
            </p>
          </div>
        </div>

        {/* Right: Demo flip button */}
        {demoAvailable && (
          <div className="flex shrink-0 items-center gap-2 self-start lg:self-center">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleFlip}
              className="gap-1.5 font-medium"
            >
              <ArrowRightLeft className="size-3.5 text-primary" aria-hidden="true" />
              <span>Flip now</span>
            </Button>
          </div>
        )}
      </div>
    </section>
  )
}
