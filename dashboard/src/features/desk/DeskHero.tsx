import { ArrowRightLeft, Clock, Moon, Sparkles, Sun } from 'lucide-react'
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
 * The Desk hero (FRONTEND_PROMPT §6, elevated with UI UX Pro Max design intelligence):
 * Large physical/digital tactile toggle switch with Priya's avatar on the day side and Scout's on the night side,
 * ambient atmospheric backlighting, metallic/glass track, active glowing knob, and live handover telemetry.
 */
export function DeskHero() {
  const { data: desk, isLoading } = useDesk()
  const now = useNow()
  const demoAvailable = useDemoStore((s) => s.available)

  if (isLoading || !desk) {
    return (
      <section
        aria-label="Client desk status"
        className="rounded-2xl border border-border/80 bg-card/80 p-5 shadow-sm"
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <Skeleton className="h-24 w-full max-w-md rounded-2xl" />
          <Skeleton className="h-14 w-64 rounded-xl" />
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
      className={cn(
        'group relative overflow-hidden rounded-2xl border transition-all duration-500 glass-card p-5 sm:p-6',
        isScout
          ? 'border-indigo-500/30 shadow-[0_4px_30px_rgba(99,102,241,0.15)]'
          : 'border-amber-500/30 shadow-[0_4px_30px_rgba(245,158,11,0.12)]',
      )}
    >
      {/* Ambient Atmospheric Mesh Glow behind the Desk */}
      <div
        className={cn(
          'pointer-events-none absolute inset-0 transition-opacity duration-700',
          isScout ? 'ambient-glow-night opacity-100' : 'ambient-glow-day opacity-100',
        )}
      />

      <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        {/* Left: Interactive Aerospace-Grade Switch with Priya and Scout */}
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3.5">
            {/* Day side: Priya */}
            <div
              className={cn(
                'flex items-center gap-2.5 rounded-xl px-3 py-2 transition-all duration-300',
                !isScout
                  ? 'bg-amber-500/10 ring-1 ring-amber-500/30 shadow-xs'
                  : 'opacity-45 hover:opacity-75',
              )}
            >
              <Avatar id="priya" size="md" />
              <div className="hidden sm:block">
                <div className="flex items-center gap-1.5 text-xs font-bold text-foreground">
                  <Sun className="size-3.5 text-amber-500" aria-hidden="true" />
                  <span>Priya</span>
                </div>
                <div className="text-[11px] font-medium text-muted-foreground">Day · Copilot</div>
              </div>
            </div>

            {/* Flagship SVG Toggle Switch */}
            <button
              type="button"
              role="switch"
              aria-checked={isScout}
              aria-label={`Client desk holder: ${holder.name} (${desk.mode} mode). Click to flip desk in demo mode.`}
              onClick={handleFlip}
              disabled={!demoAvailable}
              className={cn(
                'group relative inline-flex items-center rounded-full transition-transform active:scale-95 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring',
                demoAvailable ? 'cursor-pointer' : 'cursor-default',
              )}
            >
              <svg
                width="160"
                height="60"
                viewBox="0 0 160 60"
                aria-hidden="true"
                className="overflow-visible select-none drop-shadow-md"
              >
                <defs>
                  {/* Track gradient */}
                  <linearGradient id="switchTrackDay" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.22" />
                    <stop offset="100%" stopColor="#D97706" stopOpacity="0.08" />
                  </linearGradient>
                  <linearGradient id="switchTrackNight" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#312E81" stopOpacity="0.8" />
                    <stop offset="100%" stopColor="#4338CA" stopOpacity="0.4" />
                  </linearGradient>
                  {/* Knob gradient */}
                  <linearGradient id="knobDay" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#FFFFFF" />
                    <stop offset="100%" stopColor="#F4F4F5" />
                  </linearGradient>
                  <linearGradient id="knobNight" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#6366F1" />
                    <stop offset="100%" stopColor="#4F46E5" />
                  </linearGradient>
                  {/* Glow filter */}
                  <filter id="knobGlow" x="-50%" y="-50%" width="200%" height="200%">
                    <feDropShadow dx="0" dy="2" stdDeviation="4" floodOpacity="0.3" />
                  </filter>
                </defs>

                {/* Outer Track Border / Bevel */}
                <rect
                  x="2"
                  y="2"
                  width="156"
                  height="56"
                  rx="28"
                  className={cn(
                    'transition-all duration-400',
                    isScout
                      ? 'stroke-indigo-400/50 fill-[url(#switchTrackNight)]'
                      : 'stroke-amber-500/50 fill-[url(#switchTrackDay)]',
                  )}
                  strokeWidth="1.5"
                />

                {/* Subtle Horizon Track Markings */}
                {/* Left Day Sun Glyph */}
                <g
                  className={cn(
                    'transition-all duration-400',
                    isScout ? 'opacity-30' : 'opacity-100',
                  )}
                >
                  <circle cx="34" cy="30" r="12" className="fill-amber-500/15" />
                  <circle cx="34" cy="30" r="5" className="fill-amber-500" />
                  {/* Sun rays */}
                  <line x1="34" y1="12" x2="34" y2="15" stroke="#F59E0B" strokeWidth="1.5" strokeLinecap="round" />
                  <line x1="34" y1="45" x2="34" y2="48" stroke="#F59E0B" strokeWidth="1.5" strokeLinecap="round" />
                  <line x1="16" y1="30" x2="19" y2="30" stroke="#F59E0B" strokeWidth="1.5" strokeLinecap="round" />
                  <line x1="49" y1="30" x2="52" y2="30" stroke="#F59E0B" strokeWidth="1.5" strokeLinecap="round" />
                </g>

                {/* Right Night Moon & Stars Glyph */}
                <g
                  className={cn(
                    'transition-all duration-400',
                    isScout ? 'opacity-100' : 'opacity-30',
                  )}
                >
                  <circle cx="126" cy="30" r="12" className="fill-indigo-400/20" />
                  <path
                    d="M129 23a7 7 0 1 0 0 14 6 6 0 0 1 0-14Z"
                    className="fill-indigo-300"
                  />
                  {/* Stars */}
                  <circle cx="114" cy="22" r="1.2" className="fill-indigo-200" />
                  <circle cx="138" cy="21" r="1.4" className="fill-indigo-100" />
                  <circle cx="116" cy="39" r="1" className="fill-indigo-300" />
                </g>

                {/* Sliding Tactile Knob */}
                <g
                  filter="url(#knobGlow)"
                  style={{
                    transform: isScout ? 'translateX(96px)' : 'translateX(0px)',
                    transition: 'transform 360ms cubic-bezier(0.22, 1, 0.36, 1)',
                  }}
                >
                  <circle
                    cx="32"
                    cy="30"
                    r="23"
                    className={cn(
                      'transition-colors duration-300',
                      isScout
                        ? 'fill-[url(#knobNight)] stroke-indigo-200/60'
                        : 'fill-[url(#knobDay)] stroke-amber-500/50',
                    )}
                    strokeWidth="1.5"
                  />
                  {/* Center Emblem Text */}
                  <text
                    x="32"
                    y="34.5"
                    textAnchor="middle"
                    className={cn(
                      'font-mono text-xs font-bold tracking-tight select-none',
                      isScout ? 'fill-white' : 'fill-zinc-900',
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
                'flex items-center gap-2.5 rounded-xl px-3 py-2 transition-all duration-300',
                isScout
                  ? 'bg-indigo-500/10 ring-1 ring-indigo-500/30 shadow-xs'
                  : 'opacity-45 hover:opacity-75',
              )}
            >
              <Avatar id="scout" size="md" showVendor />
              <div className="hidden sm:block">
                <div className="flex items-center gap-1.5 text-xs font-bold text-foreground">
                  <Moon className="size-3.5 text-indigo-400" aria-hidden="true" />
                  <span>Scout</span>
                </div>
                <div className="text-[11px] font-medium text-muted-foreground">Night · Autopilot</div>
              </div>
            </div>
          </div>

          {/* Telemetry Status Section */}
          <div className="space-y-1.5 border-t border-border/80 pt-3.5 sm:border-t-0 sm:border-l sm:pt-0 sm:pl-5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-semibold text-muted-foreground">
                @client-desk
              </span>
              <SwitchTag kind="Role" label="Role · @client-desk" />
              {isScout && <SwitchTag kind="Agent · OpenCode" />}

              {/* Status pill badge with pulsing LED beacon */}
              <span
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold shadow-2xs ring-1 ring-inset',
                  isScout
                    ? 'bg-indigo-500/15 text-indigo-700 ring-indigo-500/30 dark:bg-indigo-950/60 dark:text-indigo-200'
                    : 'bg-amber-500/15 text-amber-800 ring-amber-500/30 dark:text-amber-200',
                )}
              >
                <span
                  className={cn(
                    'size-1.5 rounded-full animate-ping',
                    isScout ? 'bg-indigo-500' : 'bg-amber-500',
                  )}
                />
                <span>
                  {holder.name} · {desk.mode}
                </span>
              </span>
            </div>

            <p className="text-base sm:text-lg font-bold tracking-tight text-foreground">
              {isScout
                ? 'Scout holds the client desk on autopilot'
                : 'Priya holds the client desk in copilot mode'}
            </p>

            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <Clock className="size-3 text-muted-foreground/80" />
                <span>Until <strong className="font-semibold text-foreground">{untilDual}</strong></span>
              </span>
              <span>·</span>
              <span>
                Handover to <strong className="font-semibold text-foreground">{nextHolder.name}</strong> in{' '}
                <span className="inline-block rounded-md bg-secondary px-1.5 py-0.2 font-mono font-bold text-foreground">
                  {countdown}
                </span>
              </span>
            </div>
          </div>
        </div>

        {/* Right: Instant Flip Macro Button with Visual Flair */}
        {demoAvailable && (
          <div className="flex shrink-0 items-center gap-2.5 self-start lg:self-center">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleFlip}
              className="gap-2 font-semibold text-xs h-9 px-3.5 border-primary/30 hover:border-primary/70 hover:bg-primary/10 transition-all shadow-xs"
              title="Trigger immediate day/night desk handover"
            >
              <ArrowRightLeft className="size-3.5 text-primary transition-transform group-hover:rotate-180" aria-hidden="true" />
              <span>Flip now</span>
              <Sparkles className="size-3 text-primary/70 ml-0.5" />
            </Button>
          </div>
        )}
      </div>
    </section>
  )
}
