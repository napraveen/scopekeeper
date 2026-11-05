import { useEffect } from 'react'
import {
  FastForward,
  Pause,
  Play,
  RotateCcw,
  SkipForward,
  Sun,
  X,
  Zap,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { demo, SPEEDS, useDemoStore } from '@/lib/demo'
import { useUiStore } from '@/stores/ui'
import { cn } from '@/lib/utils'

export function DirectorMode() {
  const { available, playing, speed, cursor, total, beatIndex, beats } = useDemoStore()
  const directorOpen = useUiStore((s) => s.directorOpen)
  const setDirectorOpen = useUiStore((s) => s.setDirectorOpen)
  const toggleDirector = useUiStore((s) => s.toggleDirector)

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if typing in an input, textarea or contenteditable
      const target = e.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return
      }

      if (e.key === 'd' || e.key === 'D') {
        e.preventDefault()
        toggleDirector()
        return
      }

      if (!directorOpen || !available) return

      if (e.code === 'Space') {
        e.preventDefault()
        if (playing) demo().pause()
        else demo().play()
      } else if (e.key === '.') {
        e.preventDefault()
        demo().step()
      } else if (e.key === ']') {
        e.preventDefault()
        demo().nextBeat()
      } else if (e.key === '[') {
        e.preventDefault()
        demo().prevBeat()
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault()
        demo().reset()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [directorOpen, available, playing, toggleDirector])

  if (!available || !directorOpen) return null

  return (
    <div
      role="region"
      aria-label="Director control panel"
      className="fixed bottom-5 right-5 z-50 w-80 sm:w-96 rounded-2xl border border-border/90 bg-card/95 p-4 shadow-2xl backdrop-blur-md animate-in fade-in slide-in-from-bottom-4 duration-200"
    >
      <div className="flex items-center justify-between pb-3 border-b border-border/70">
        <div className="flex items-center gap-2">
          <Zap className="size-4 text-primary" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">
            Director Mode
          </h3>
          <span className="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-primary">
            {cursor} / {total}
          </span>
        </div>

        <button
          type="button"
          onClick={() => setDirectorOpen(false)}
          className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground"
          aria-label="Close director panel"
        >
          <X className="size-4" />
        </button>
      </div>

      {/* Main playback controls */}
      <div className="mt-3 flex items-center justify-between gap-1">
        <Button
          type="button"
          size="sm"
          variant={playing ? 'secondary' : 'default'}
          onClick={() => (playing ? demo().pause() : demo().play())}
          className="gap-1.5 font-semibold text-xs flex-1"
        >
          {playing ? <Pause className="size-3.5" /> : <Play className="size-3.5" />}
          <span>{playing ? 'Pause' : 'Play'}</span>
        </Button>

        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => demo().step()}
          title="Step next event (Hotkey: .)"
          className="gap-1 text-xs"
        >
          <SkipForward className="size-3.5" />
          <span>Step</span>
        </Button>

        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => demo().reset()}
          title="Reset story (Hotkey: R)"
          className="gap-1 text-xs"
        >
          <RotateCcw className="size-3.5" />
          <span>Reset</span>
        </Button>
      </div>

      {/* Speed controls */}
      <div className="mt-3 flex items-center justify-between gap-1 rounded-lg bg-secondary/50 p-1">
        <span className="text-[11px] font-medium text-muted-foreground pl-2 flex items-center gap-1">
          <FastForward className="size-3" /> Speed:
        </span>
        <div className="flex gap-1">
          {SPEEDS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => demo().setSpeed(s)}
              className={cn(
                'rounded px-2 py-0.5 font-mono text-xs font-semibold transition-colors',
                speed === s
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'text-muted-foreground hover:bg-secondary hover:text-foreground',
              )}
            >
              {s}×
            </button>
          ))}
        </div>
      </div>

      {/* Fast macro buttons: Flip now, Morning now */}
      <div className="mt-2.5 grid grid-cols-2 gap-2">
        <Button
          type="button"
          size="xs"
          variant="secondary"
          onClick={() => demo().flipNow()}
          className="text-[11px]"
        >
          Flip desk now
        </Button>
        <Button
          type="button"
          size="xs"
          variant="secondary"
          onClick={() => demo().morningNow()}
          className="text-[11px]"
        >
          <Sun className="size-3 text-day mr-1" /> Morning now
        </Button>
      </div>

      {/* Ten beats dropdown / picker */}
      <div className="mt-3 pt-2.5 border-t border-border/70 space-y-1.5">
        <div className="flex justify-between items-center text-[11px] font-medium text-muted-foreground">
          <span>Jump to Beat (hotkeys [ and ]):</span>
          <span className="font-mono text-foreground font-semibold">
            {beatIndex >= 0 ? `${beatIndex + 1}/${beats.length}` : 'Start'}
          </span>
        </div>

        <div className="max-h-36 overflow-y-auto space-y-1 pr-1 scrollbar-thin">
          {beats.map((beat, idx) => {
            const isCurrent = beatIndex === idx
            return (
              <button
                key={beat.id}
                type="button"
                onClick={() => demo().jumpToBeat(beat.id)}
                className={cn(
                  'w-full flex items-center justify-between rounded-md px-2 py-1 text-left text-xs transition-colors',
                  isCurrent
                    ? 'bg-primary/15 font-semibold text-primary'
                    : 'text-muted-foreground hover:bg-secondary/70 hover:text-foreground',
                )}
              >
                <span>
                  {idx + 1}. {beat.label}
                </span>
                {isCurrent && <span className="text-[10px] font-bold">● Active</span>}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
