import { Bot } from 'lucide-react'
import { person } from '@/lib/people'
import { cn } from '@/lib/utils'
import { AgentBadge } from './AgentBadge'

const SIZES = {
  xs: 'size-5 text-[10px]',
  sm: 'size-6 text-xs',
  md: 'size-8 text-xs',
  lg: 'size-10 text-sm',
} as const

export function Avatar({
  id,
  size = 'sm',
  showName = false,
  showVendor = false,
  className,
}: {
  id: string | undefined
  size?: keyof typeof SIZES
  showName?: boolean
  showVendor?: boolean
  className?: string
}) {
  const p = person(id)
  const isAgent = p.kind === 'agent'
  const isClient = p.side === 'client'

  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      <span
        title={`${p.name}${p.title ? ` · ${p.title}` : ''}`}
        aria-label={p.name}
        className={cn(
          'inline-flex shrink-0 items-center justify-center font-semibold select-none ring-1 ring-inset',
          SIZES[size],
          isAgent
            ? 'rounded-md bg-brand-soft text-accent-foreground ring-primary/30'
            : isClient
              ? 'rounded-full bg-amber-500/15 text-amber-800 ring-amber-500/30 dark:text-amber-200'
              : 'rounded-full bg-secondary text-secondary-foreground ring-border',
        )}
      >
        {isAgent ? (
          <Bot className={size === 'xs' ? 'size-3' : size === 'lg' ? 'size-5' : 'size-3.5'} aria-hidden="true" />
        ) : (
          p.initial
        )}
      </span>
      {showName && <span className="text-sm font-medium text-foreground">{p.name}</span>}
      {showVendor && p.vendor && <AgentBadge vendor={p.vendor} />}
    </span>
  )
}
