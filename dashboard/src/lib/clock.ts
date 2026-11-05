/**
 * The app's notion of "now". In mock mode the story engine drives it (simulated time);
 * in live mode it follows the wall clock, corrected by the server's time from `/api/health`.
 */
import { useEffect } from 'react'
import { create } from 'zustand'

interface ClockState {
  now: number
  driven: boolean
}

export const useClockStore = create<ClockState>(() => ({ now: Date.now(), driven: false }))

/** The story engine calls this on each tick. */
export function driveClock(now: number): void {
  useClockStore.setState({ now, driven: true })
}

let skewMs = 0
export function setServerTime(iso: string): void {
  skewMs = new Date(iso).getTime() - Date.now()
}

/** Keeps the wall clock ticking when nothing drives it. Mount once. */
export function useWallClock(): void {
  useEffect(() => {
    const id = window.setInterval(() => {
      if (!useClockStore.getState().driven) useClockStore.setState({ now: Date.now() + skewMs })
    }, 1000)
    return () => window.clearInterval(id)
  }, [])
}

export function useNow(): number {
  return useClockStore((s) => s.now)
}
