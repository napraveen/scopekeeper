import { FileText } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useScope } from '@/lib/api/queries'
import { cn } from '@/lib/utils'

export function ClauseBadge({
  clauseId,
  className,
}: {
  clauseId: string
  className?: string
}) {
  const { data: scope } = useScope()
  const clause = scope?.clauses.find((c) => c.id === clauseId)

  const pill = (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded border border-border bg-secondary/60 px-1.5 py-0.5 font-mono text-[11px] leading-none font-medium text-foreground',
        className,
      )}
    >
      <FileText className="size-2.5 text-muted-foreground" aria-hidden="true" />
      <span>§{clauseId}</span>
    </span>
  )

  if (!clause) return pill

  return (
    <Tooltip>
      <TooltipTrigger asChild>{pill}</TooltipTrigger>
      <TooltipContent className="max-w-xs space-y-1 p-2.5 text-xs">
        <div className="font-semibold">
          Clause {clause.id} · {clause.title}{' '}
          <span className="font-normal text-muted-foreground">
            ({clause.kind === 'in' ? 'In scope' : 'Excluded'})
          </span>
        </div>
        <p className="text-muted-foreground leading-relaxed">“{clause.excerpt}”</p>
      </TooltipContent>
    </Tooltip>
  )
}
