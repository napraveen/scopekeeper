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

  const progressPct = total > 0 ? Math.min(100, Math.round((cursor / total) * 100)) : 0

  return (
    <div
      role="region"
      aria-label="Director control panel"
      className="fixed bottom-5 right-5 z-50 w-84 sm:w-96 rounded-2xl border border-zinc-700/80 bg-zinc-950/95 text-zinc-100 p-4 shadow-[0_20px_50px_rgba(0,0,0,0.6)] backdrop-blur-xl animate-in fade-in slide-in-from-bottom-4 duration-200 select-none"
    >
      {/* Header with live record dot */}
      <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <span className="relative flex size-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-400 opacity-75" />
            <span className="relative inline-flex size-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.8)]" />
          </span>
          <div className="flex items-center gap-1.5">
            <Zap className="size-3.5 text-amber-400" />
            <h3 className="text-xs font-black uppercase tracking-wider text-white">
              Director Mode
            </h3>
          </div>
          <span className="rounded bg-zinc-800/80 px-2 py-0.5 font-mono text-[10px] font-bold text-indigo-400 border border-zinc-700">
            {cursor} / {total}
          </span>
        </div>

        <button
          type="button"
          onClick={() => setDirectorOpen(false)}
          className="rounded-md p-1 text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
          aria-label="Close director panel"
        >
          <X className="size-4" />
        </button>
      </div>

      {/* Story Progress Bar */}
      <div className="mt-2.5 h-1.5 w-full bg-zinc-800/80 rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-500 transition-all duration-300 shadow-[0_0_8px_rgba(99,102,241,0.6)]"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Main playback controls */}
      <div className="mt-3 flex items-center justify-between gap-1.5">
        <Button
          type="button"
          size="sm"
          variant={playing ? 'secondary' : 'default'}
          onClick={() => (playing ? demo().pause() : demo().play())}
          className={cn(
            'gap-1.5 font-bold text-xs flex-1 h-8 shadow-xs',
            !playing && 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-[0_0_12px_rgba(79,70,229,0.4)]',
          )}
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
          className="gap-1 text-xs h-8 bg-zinc-900 border-zinc-700 text-zinc-200 hover:bg-zinc-800 hover:text-white"
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
          className="gap-1 text-xs h-8 bg-zinc-900 border-zinc-700 text-zinc-200 hover:bg-zinc-800 hover:text-white"
        >
          <RotateCcw className="size-3.5" />
          <span>Reset</span>
        </Button>
      </div>

      {/* Speed controls */}
      <div className="mt-3 flex items-center justify-between gap-1 rounded-xl bg-zinc-900/90 border border-zinc-800/80 p-1">
        <span className="text-[11px] font-semibold text-zinc-400 pl-2 flex items-center gap-1">
          <FastForward className="size-3 text-indigo-400" /> Speed:
        </span>
        <div className="flex gap-1">
          {SPEEDS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => demo().setSpeed(s)}
              className={cn(
                'rounded-lg px-2.5 py-0.5 font-mono text-xs font-bold transition-all',
                speed === s
                  ? 'bg-indigo-600 text-white shadow-[0_0_8px_rgba(79,70,229,0.5)]'
                  : 'text-zinc-400 hover:bg-zinc-800 hover:text-white',
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
          className="text-[11px] font-semibold h-7 bg-zinc-900 border border-zinc-800 text-zinc-200 hover:bg-zinc-800 hover:text-white"
        >
          Flip desk now
        </Button>
        <Button
          type="button"
          size="xs"
          variant="secondary"
          onClick={() => demo().morningNow()}
          className="text-[11px] font-semibold h-7 bg-zinc-900 border border-zinc-800 text-amber-400 hover:bg-zinc-800 hover:text-amber-300"
        >
          <Sun className="size-3 mr-1" /> Morning now
        </Button>
      </div>

      {/* Ten beats dropdown / picker */}
      <div className="mt-3 pt-2.5 border-t border-zinc-800 space-y-1.5">
        <div className="flex justify-between items-center text-[11px] font-semibold text-zinc-400">
          <span>Jump to Beat (<kbd className="font-mono text-zinc-300">[</kbd> and <kbd className="font-mono text-zinc-300">]</kbd>):</span>
          <span className="font-mono text-indigo-400 font-bold">
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
                  'w-full flex items-center justify-between rounded-lg px-2.5 py-1 text-left text-xs transition-colors',
                  isCurrent
                    ? 'bg-indigo-600/30 border border-indigo-500/50 font-bold text-white shadow-2xs'
                    : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200',
                )}
              >
                <span>
                  {idx + 1}. {beat.label}
                </span>
                {isCurrent && <span className="text-[10px] font-bold text-indigo-400">● Active</span>}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
