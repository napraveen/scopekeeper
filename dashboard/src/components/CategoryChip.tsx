import { CATEGORY } from '@/lib/categories'
import type { Category } from '@/lib/api/types'
import { cn } from '@/lib/utils'

/**
 * Category chip: icon + text label + colour (colour is never the only signal).
 */
export function CategoryChip({
  category,
  size = 'sm',
  className,
}: {
  category?: Category
  size?: 'xs' | 'sm'
  className?: string
}) {
  if (!category) {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1 rounded-md bg-muted px-1.5 py-0.5 text-xs font-medium text-muted-foreground ring-1 ring-inset ring-border',
          size === 'xs' && 'px-1.5 py-0 text-[11px]',
          className,
        )}
      >
        Sorting…
      </span>
    )
  }
  const meta = CATEGORY[category]
  const Icon = meta.icon
  return (
    <span
      title={meta.hint}
      className={cn(
        'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium ring-1 ring-inset',
        size === 'xs' && 'px-1.5 py-0 text-[11px]',
        meta.className,
        className,
      )}
    >
      <Icon className="size-3 shrink-0" aria-hidden="true" />
      <span>{meta.label}</span>
    </span>
  )
}
