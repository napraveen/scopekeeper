import { describe, expect, it } from 'vitest'
import {
  formatCountdown,
  formatDual,
  formatHours,
  formatMoney,
  formatRelative,
  setCurrency,
} from '../lib/format'

describe('money formatter', () => {
  it('formats whole cents without fractional part', () => {
    expect(formatMoney(203000)).toBe('$2,030')
    expect(formatMoney(14000)).toBe('$140')
    expect(formatMoney(0)).toBe('$0')
  })

  it('formats fractional cents with 2 digits', () => {
    expect(formatMoney(14050)).toBe('$140.50')
    expect(formatMoney(1099)).toBe('$10.99')
  })

  it('respects currency settings', () => {
    setCurrency('EUR')
    expect(formatMoney(10000)).toContain('100')
    setCurrency('USD')
  })
})

describe('hours formatter', () => {
  it('formats hours with decimal only when needed', () => {
    expect(formatHours(3)).toBe('3 h')
    expect(formatHours(2.5)).toBe('2.5 h')
    expect(formatHours(190)).toBe('190 h')
    expect(formatHours(56.0)).toBe('56 h')
  })

  it('formats without unit when requested', () => {
    expect(formatHours(2.5, { unit: false })).toBe('2.5')
  })
})

describe('time formatters', () => {
  const ts = '2026-11-05T20:30:00+05:30'

  it('formats dual time zones always', () => {
    const dual = formatDual(ts)
    expect(dual).toContain('IST')
    expect(dual).toContain('ET')
    expect(dual).toBe('8:30 PM IST · 10:00 AM ET')
  })

  it('formats relative time correctly', () => {
    const now = new Date('2026-11-05T20:35:00+05:30').getTime()
    expect(formatRelative(ts, now)).toBe('5 min ago')
  })

  it('formats countdown', () => {
    expect(formatCountdown(2 * 3600_000 + 14 * 60_000)).toBe('2 h 14 min')
    expect(formatCountdown(9 * 60_000)).toBe('9 min')
    expect(formatCountdown(45_000)).toBe('45 s')
    expect(formatCountdown(0)).toBe('now')
  })
})
