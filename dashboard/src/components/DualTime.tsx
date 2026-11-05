import { formatDual, formatRelative } from '@/lib/format'
import { useNow } from '@/lib/clock'
import { cn } from '@/lib/utils'

/**
 * Always renders both zones (`8:30 PM IST · 10:00 AM ET`), optionally preceded by relative time.
 */
export function DualTime({
  iso,
  withDay = false,
  relative = false,
  className,
}: {
  iso: string
  withDay?: boolean
  relative?: boolean
  className?: string
}) {
  const now = useNow()
  const dual = formatDual(iso, { withDay })
  const rel = relative ? formatRelative(iso, now) : null

  return (
    <time
      dateTime={iso}
      title={formatDual(iso, { withDay: true })}
      className={cn('tabular text-xs text-muted-foreground', className)}
    >
      {rel ? `${rel} · ${dual}` : dual}
    </time>
  )
}
