import type { Member } from '@/lib/api/types'
import { cn } from '@/lib/utils'

/**
 * Text badge for agent vendors, never their logos (FRONTEND_PROMPT §2).
 */
export function AgentBadge({
  vendor,
  className,
}: {
  vendor: NonNullable<Member['vendor']>
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded border border-border bg-secondary/70 px-1.5 py-0.5 font-mono text-[10px] leading-none font-medium tracking-tight text-muted-foreground',
        className,
      )}
    >
      {vendor}
    </span>
  )
}
