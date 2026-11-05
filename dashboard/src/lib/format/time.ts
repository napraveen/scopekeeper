import { format } from 'date-fns'
import { TZDate } from '@date-fns/tz'

export const ZONES = {
  agency: { tz: 'Asia/Kolkata', label: 'IST', city: 'Mumbai' },
  client: { tz: 'America/New_York', label: 'ET', city: 'New York' },
} as const

export type ZoneKey = keyof typeof ZONES

function toDate(input: string | number | Date): Date {
  return input instanceof Date ? input : new Date(input)
}

/** `8:30 PM` in the given zone. */
export function formatClock(input: string | number | Date, zone: ZoneKey): string {
  return format(new TZDate(toDate(input).getTime(), ZONES[zone].tz), 'h:mm a')
}

/** `8:30 PM IST` */
export function formatZoned(input: string | number | Date, zone: ZoneKey): string {
  return `${formatClock(input, zone)} ${ZONES[zone].label}`
}

/** `Nov 5` in the given zone. */
export function formatDay(input: string | number | Date, zone: ZoneKey): string {
  return format(new TZDate(toDate(input).getTime(), ZONES[zone].tz), 'MMM d')
}

/** Hour of day (0–23, fractional) in the zone, for working-hours bars. */
export function hourOfDay(input: string | number | Date, zone: ZoneKey): number {
  const d = new TZDate(toDate(input).getTime(), ZONES[zone].tz)
  return d.getHours() + d.getMinutes() / 60
}

/**
 * Both zones, always: `8:30 PM IST · 10:00 AM ET`.
 * With `withDay`, the day is added to each side, and only differs when the zones disagree:
 * `Nov 6, 9:30 AM IST · Nov 5, 11:00 PM ET`.
 */
export function formatDual(input: string | number | Date, opts: { withDay?: boolean } = {}): string {
  const ist = formatZoned(input, 'agency')
  const et = formatZoned(input, 'client')
  if (!opts.withDay) return `${ist} · ${et}`
  return `${formatDay(input, 'agency')}, ${ist} · ${formatDay(input, 'client')}, ${et}`
}

/** `just now`, `3 min ago`, `2 h ago`, `yesterday`, `4 days ago` relative to `now`. */
export function formatRelative(input: string | number | Date, now: number): string {
  const diffSec = Math.round((now - toDate(input).getTime()) / 1000)
  if (diffSec < 45) return diffSec < -45 ? 'soon' : 'just now'
  const min = Math.round(diffSec / 60)
  if (min < 60) return `${min} min ago`
  const h = Math.round(min / 60)
  if (h < 24) return `${h} h ago`
  const d = Math.round(h / 24)
  return d === 1 ? 'yesterday' : `${d} days ago`
}

/** Countdown `2 h 14 min`, `9 min`, `45 s`. */
export function formatCountdown(ms: number): string {
  if (ms <= 0) return 'now'
  const totalSec = Math.floor(ms / 1000)
  const h = Math.floor(totalSec / 3600)
  const m = Math.floor((totalSec % 3600) / 60)
  if (h > 0) return `${h} h ${m} min`
  if (m > 0) return `${m} min`
  return `${totalSec} s`
}
