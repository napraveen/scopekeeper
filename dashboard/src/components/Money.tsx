import { useEffect, useRef, useState } from 'react'
import { formatMoney } from '@/lib/format'
import { cn } from '@/lib/utils'

/**
 * Tabular money figure. When `animate` is on, ticks smoothly between values
 * unless `prefers-reduced-motion` is set.
 */
export function Money({
  cents,
  animate = false,
  className,
}: {
  cents: number
  animate?: boolean
  className?: string
}) {
  const [displayed, setDisplayed] = useState(cents)
  const prevRef = useRef(cents)

  useEffect(() => {
    const from = prevRef.current
    prevRef.current = cents
    if (!animate || from === cents) {
      setDisplayed(cents)
      return
    }
    const reduce =
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduce) {
      setDisplayed(cents)
      return
    }
    const duration = 450
    const start = performance.now()
    let raf = 0
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      setDisplayed(Math.round(from + (cents - from) * eased))
      if (t < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [cents, animate])

  return (
    <span className={cn('tabular', className)} data-cents={cents}>
      {formatMoney(animate ? displayed : cents)}
    </span>
  )
}
