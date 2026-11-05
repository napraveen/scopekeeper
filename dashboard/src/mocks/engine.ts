/**
 * The in-browser story engine. It replays `STORY` on a simulated clock, mutates the mock
 * database and emits each step through the same `StreamSource` interface the live SSE uses.
 */
import { driveClock } from '@/lib/clock'
import { useDemoStore, type DemoController } from '@/lib/demo'
import type { StreamHandlers, StreamSource } from '@/lib/api/stream'
import type { StreamEvent } from '@/lib/api/types'
import { db, resetDb } from './db'
import { STORY_START } from './seed'
import { BEATS, STORY, type StoryStep } from './story'

export interface EngineOptions {
  speed?: number
  autoplay?: boolean
  tickMs?: number
  /** Publish state to the app stores (off in unit tests). */
  publish?: boolean
}

const ms = (iso: string) => new Date(iso).getTime()

export class StoryEngine implements StreamSource, DemoController {
  private readonly steps: StoryStep[]
  private readonly tickMs: number
  private readonly shouldPublish: boolean
  private readonly beatIdx: number[]
  private cursor = 0
  private clock = ms(STORY_START)
  private speed: number
  private playing = false
  private timer: ReturnType<typeof setInterval> | undefined
  private adhoc = 0
  private readonly listeners = new Set<StreamHandlers>()

  constructor(steps: StoryStep[] = STORY, opts: EngineOptions = {}) {
    this.steps = [...steps].sort((a, b) => ms(a.ts) - ms(b.ts))
    this.speed = opts.speed ?? 60
    this.tickMs = opts.tickMs ?? 100
    this.shouldPublish = opts.publish ?? true
    this.beatIdx = BEATS.map((b) => this.steps.findIndex((s) => s.beat === b.id))
    this.publish()
    if (opts.autoplay) this.play()
  }

  // ------------------------------------------------------------ StreamSource

  subscribe(handlers: StreamHandlers): () => void {
    this.listeners.add(handlers)
    handlers.onStatus('open')
    return () => {
      this.listeners.delete(handlers)
    }
  }

  // ------------------------------------------------------------ inspection (tests, director)

  get now(): number {
    return this.clock
  }
  get position(): number {
    return this.cursor
  }
  get length(): number {
    return this.steps.length
  }
  get isPlaying(): boolean {
    return this.playing
  }

  // ------------------------------------------------------------ DemoController

  play(): void {
    if (this.playing || this.cursor >= this.steps.length) return
    this.playing = true
    this.timer = setInterval(() => this.tick(), this.tickMs)
    this.publish()
  }

  pause(): void {
    this.playing = false
    if (this.timer) clearInterval(this.timer)
    this.timer = undefined
    this.publish()
  }

  setSpeed(speed: number): void {
    this.speed = speed
    this.publish()
  }

  /** Emit the next event now. */
  step(): void {
    const next = this.steps[this.cursor]
    if (!next) return
    this.clock = Math.max(this.clock, ms(next.ts))
    this.applyAt(this.cursor, true)
    this.cursor += 1
    this.publish()
  }

  nextBeat(): void {
    const target = this.beatIdx.find((i) => i >= this.cursor)
    if (target !== undefined) this.jumpTo(target)
  }

  prevBeat(): void {
    const reached = this.beatIdx.filter((i) => i < this.cursor)
    const target = reached[reached.length - 2]
    if (target === undefined) this.reset()
    else this.jumpTo(target)
  }

  jumpToBeat(id: string): void {
    const i = this.steps.findIndex((s) => s.beat === id)
    if (i !== -1) this.jumpTo(i)
  }

  flipNow(): void {
    const i = this.steps.findIndex((s, idx) => idx >= this.cursor && s.type === 'desk.handover')
    if (i !== -1) this.jumpTo(i)
  }

  morningNow(): void {
    this.jumpToBeat('morning-handover')
  }

  reset(): void {
    this.pause()
    resetDb()
    this.cursor = 0
    this.clock = ms(STORY_START)
    this.sync()
    this.publish()
  }

  /**
   * Fast-forward silently to just before step `target`, then emit it (and anything at the
   * same moment) visibly. Jumping backwards resets first.
   */
  jumpTo(target: number): void {
    const step = this.steps[target]
    if (!step) return
    if (target < this.cursor) {
      resetDb()
      this.cursor = 0
    }
    while (this.cursor < target) {
      this.applyAt(this.cursor, false)
      this.cursor += 1
    }
    this.clock = ms(step.ts)
    this.sync()
    this.flush(true)
    this.publish()
  }

  /** For dashboard actions in mock mode: mutate the db and emit an event at the story's "now". */
  emitAdHoc(event: Omit<StreamEvent, 'id' | 'ts'>, apply?: () => void): StreamEvent {
    apply?.()
    this.adhoc += 1
    const ev: StreamEvent = { ...event, id: `adhoc-${this.adhoc}`, ts: new Date(this.clock).toISOString() }
    db.current.events.push(ev)
    for (const l of this.listeners) l.onEvent(ev)
    return ev
  }

  dispose(): void {
    this.pause()
    this.listeners.clear()
  }

  // ------------------------------------------------------------ internals

  private tick(): void {
    this.clock += this.tickMs * this.speed
    this.flush(true)
    if (this.cursor >= this.steps.length) this.pause()
    this.publish()
  }

  private flush(visible: boolean): void {
    while (this.cursor < this.steps.length && ms(this.steps[this.cursor]!.ts) <= this.clock) {
      this.applyAt(this.cursor, visible)
      this.cursor += 1
    }
  }

  private applyAt(index: number, visible: boolean): void {
    const step = this.steps[index]
    if (!step) return
    const d = db.current
    if (step.skipIf?.(d)) return
    step.apply?.(d)
    const { apply: _a, beat: _b, skipIf: _s, ...rest } = step
    const ev: StreamEvent = { ...rest, id: `evt-${index}` }
    d.events.push(ev)
    if (visible) for (const l of this.listeners) l.onEvent(ev)
  }

  private sync(): void {
    for (const l of this.listeners) l.onSync()
  }

  private publish(): void {
    if (!this.shouldPublish) return
    driveClock(this.clock)
    const reached = this.beatIdx.filter((i) => i >= 0 && i < this.cursor).length - 1
    useDemoStore.setState({
      playing: this.playing,
      speed: this.speed,
      cursor: this.cursor,
      total: this.steps.length,
      beatIndex: reached,
      beats: BEATS,
    })
  }
}

let engine: StoryEngine | null = null

export function getEngine(): StoryEngine | null {
  return engine
}

export function startEngine(opts: EngineOptions = {}): StoryEngine {
  engine?.dispose()
  engine = new StoryEngine(STORY, opts)
  return engine
}
