let currency = 'USD'
const cache = new Map<string, Intl.NumberFormat>()

/** Currency is a setting; default USD. */
export function setCurrency(code: string): void {
  currency = code
}

export function getCurrency(): string {
  return currency
}

function formatter(code: string, fractionDigits: number): Intl.NumberFormat {
  const key = `${code}:${fractionDigits}`
  let f = cache.get(key)
  if (!f) {
    f = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: code,
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    })
    cache.set(key, f)
  }
  return f
}

/**
 * Integer cents to money. Whole amounts drop the cents: 203000 → `$2,030`; 14050 → `$140.50`.
 */
export function formatMoney(cents: number, code: string = currency): string {
  const whole = cents % 100 === 0
  return formatter(code, whole ? 0 : 2).format(cents / 100)
}
