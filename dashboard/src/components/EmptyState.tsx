import type { LucideIcon } from 'lucide-react'
import { Inbox } from 'lucide-react'
import { cn } from '@/lib/utils'

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: {
  icon?: LucideIcon
  title: string
  description: string
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/50 px-6 py-8 text-center',
        className,
      )}
    >
      <div className="mb-2.5 flex size-9 items-center justify-center rounded-lg border border-border bg-secondary/60 text-muted-foreground">
        <Icon className="size-4" aria-hidden="true" />
      </div>
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="mt-1 max-w-md text-xs text-muted-foreground leading-relaxed">{description}</p>
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}
