/**
 * The demo controller: one interface for the story controls, whether the story runs in the
 * browser (mock mode) or on the backend (`/api/demo/*`, live mode).
 */
import { create } from 'zustand'
import { api } from '@/lib/api/client'

export interface DemoBeat {
  id: string
  label: string
}

export const BEATS: DemoBeat[] = [
  { id: 'flip', label: 'The Flip' },
  { id: 'sam-message', label: "Sam's message" },
  { id: 'sorted', label: 'Sorted in a minute' },
  { id: 'excel-approved', label: 'Excel approved' },
  { id: 'android-estimate', label: 'Android estimate' },
  { id: 'previews-up', label: 'Previews up' },
  { id: 'dark-mode-accepted', label: 'Dark mode accepted' },
  { id: 'morning-handover', label: 'Morning handover' },
  { id: 'options-approved', label: 'Options approved' },
  { id: 'sam-picks-d', label: 'Sam picks D' },
]

export interface DemoState {
  available: boolean
  playing: boolean
  speed: number
  /** Index of the next event to emit, and the total. */
  cursor: number
  total: number
  /** Index into `beats` of the last beat reached, or -1. */
  beatIndex: number
  beats: DemoBeat[]
}

export interface DemoController {
  play(): void
  pause(): void
  setSpeed(speed: number): void
  step(): void
  nextBeat(): void
  prevBeat(): void
  jumpToBeat(id: string): void
  flipNow(): void
  morningNow(): void
  reset(): void
}

export const SPEEDS = [1, 10, 60, 600] as const

export const useDemoStore = create<DemoState>(() => ({
  available: false,
  playing: false,
  speed: 60,
  cursor: 0,
  total: 20,
  beatIndex: -1,
  beats: BEATS,
}))

const noop = () => undefined

let controller: DemoController = {
  play: noop,
  pause: noop,
  setSpeed: noop,
  step: noop,
  nextBeat: noop,
  prevBeat: noop,
  jumpToBeat: noop,
  flipNow: noop,
  morningNow: noop,
  reset: noop,
}

export function registerDemoController(c: DemoController): void {
  controller = c
  useDemoStore.setState({ available: true, beats: BEATS })
}

export function demo(): DemoController {
  return controller
}

/**
 * In live mode, the same controls call `/api/demo/*` instead (§10).
 */
export function createLiveDemoController(): DemoController {
  return {
    play: () => {
      useDemoStore.setState({ playing: true })
      void api.demo.clock({ playing: true })
    },
    pause: () => {
      useDemoStore.setState({ playing: false })
      void api.demo.clock({ playing: false })
    },
    setSpeed: (speed) => {
      useDemoStore.setState({ speed })
      void api.demo.clock({ speed })
    },
    step: () => {
      void api.demo.clock({ step: true })
    },
    nextBeat: () => {
      const { beatIndex, beats } = useDemoStore.getState()
      const nextIdx = Math.min(beats.length - 1, beatIndex + 1)
      const target = beats[nextIdx]
      if (target) {
        useDemoStore.setState({ beatIndex: nextIdx })
        void api.demo.clock({ beat: target.id })
      }
    },
    prevBeat: () => {
      const { beatIndex, beats } = useDemoStore.getState()
      const prevIdx = Math.max(0, beatIndex - 1)
      const target = beats[prevIdx]
      if (target) {
        useDemoStore.setState({ beatIndex: prevIdx })
        void api.demo.clock({ beat: target.id })
      }
    },
    jumpToBeat: (id) => {
      const idx = BEATS.findIndex((b) => b.id === id)
      useDemoStore.setState({ beatIndex: idx })
      void api.demo.clock({ beat: id })
    },
    flipNow: () => {
      void api.demo.flip()
    },
    morningNow: () => {
      void api.demo.morning()
    },
    reset: () => {
      useDemoStore.setState({ cursor: 0, beatIndex: -1, playing: false })
      void api.demo.clock({ reset: true })
    },
  }
}
