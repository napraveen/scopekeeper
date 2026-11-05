const oneDecimal = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

/** Hours with a decimal only when needed: 3 → `3 h`, 2.5 → `2.5 h`, 190 → `190 h`. */
export function formatHours(hours: number, opts: { unit?: boolean } = {}): string {
  const n = oneDecimal.format(Math.round(hours * 10) / 10)
  return opts.unit === false ? n : `${n} h`
}
