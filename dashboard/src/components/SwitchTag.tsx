import { Layers } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { useUiStore } from '@/stores/ui'

export type SwitchKind =
  | 'Room'
  | 'Role'
  | 'Room link'
  | 'Reference'
  | 'Agent · OpenCode'
  | 'Agent · Claude Code'
  | 'Agent · Codex'
  | 'Agent · Custom'
  | 'Membership boundary'

const TOOLTIPS: Record<SwitchKind, string> = {
  Room: 'A shared chat channel bridged across Slack, Discord, Teams or Mattermost.',
  Role: 'A role reaches whoever holds it right now, person or agent.',
  'Room link': 'Routes messages and artifacts between rooms according to explicit rules.',
  Reference: 'Shared context (SOW, plan, repo) pinned to the room so agents ground every reply.',
  'Agent · OpenCode': 'An OpenCode agent running as a first-class participant in the room.',
  'Agent · Claude Code': 'A Claude Code agent reading the repository to size work from real code.',
  'Agent · Codex': 'A Codex agent that opens branches, pull requests and preview environments.',
  'Agent · Custom': 'A custom Switch agent checking asks against the signed scope of work.',
  'Membership boundary': 'Internal rooms stay private; client-facing agents cannot read internal pricing.',
}

/**
 * Small outlined tag shown only when the Switch lens is on (FRONTEND_PROMPT §5).
 */
export function SwitchTag({
  kind,
  label,
  className,
}: {
  kind: SwitchKind
  label?: string
  className?: string
}) {
  const on = useUiStore((s) => s.switchLens)
  if (!on) return null

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            'inline-flex items-center gap-1 rounded border border-dashed border-primary/60 bg-accent/60 px-1.5 py-0.5 font-mono text-[10px] leading-none font-medium text-accent-foreground',
            className,
          )}
        >
          <Layers className="size-2.5 text-primary" aria-hidden="true" />
          <span>{label ?? kind}</span>
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">{TOOLTIPS[kind]}</TooltipContent>
    </Tooltip>
  )
}
