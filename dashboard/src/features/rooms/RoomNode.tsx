import { Handle, Position } from '@xyflow/react'
import { FileText, Hash } from 'lucide-react'
import { Avatar } from '@/components/Avatar'
import type { Room } from '@/lib/api/types'
import { person } from '@/lib/people'
import { cn } from '@/lib/utils'

export function RoomNode({ data }: { data: Room & { pulsed?: boolean } }) {
  const isClient = data.kind === 'client'
  const isChange = data.kind === 'change'

  return (
    <div
      className={cn(
        'w-72 rounded-xl border-2 bg-card p-3.5 shadow-md transition-all',
        data.pulsed && 'animate-glow ring-2 ring-primary',
        isClient
          ? 'border-amber-500/60 shadow-amber-500/10'
          : isChange
            ? 'border-violet-500/60 shadow-violet-500/10'
            : 'border-primary/60 shadow-primary/10',
      )}
    >
      <Handle type="target" position={Position.Left} className="size-2.5 bg-primary border-2 border-background" />
      <Handle type="source" position={Position.Right} className="size-2.5 bg-primary border-2 border-background" />

      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-border/60">
        <div className="flex items-center gap-1.5 font-mono text-xs font-bold text-foreground">
          <Hash className="size-3.5 text-primary" />
          <span>{data.name}</span>
        </div>

        <span
          className={cn(
            'rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider',
            data.app === 'discord'
              ? 'bg-amber-500/15 text-amber-800 dark:text-amber-200'
              : 'bg-primary/10 text-primary',
          )}
        >
          {data.app}
        </span>
      </div>

      {/* Role Holders */}
      {data.roles.length > 0 && (
        <div className="mt-2 space-y-1">
          {data.roles.map((r) => (
            <div key={r.name} className="flex items-center justify-between text-[11px]">
              <span className="font-mono text-muted-foreground">{r.name}:</span>
              <span className="font-semibold text-foreground flex items-center gap-1">
                <Avatar id={r.holder} size="xs" />
                <span>{person(r.holder).name}</span>
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Members avatars list */}
      <div className="mt-3 flex items-center justify-between pt-2 border-t border-border/40">
        <span className="text-[10px] text-muted-foreground uppercase font-medium">Members</span>
        <div className="flex items-center -space-x-1.5 overflow-hidden">
          {data.members.map((m) => (
            <Avatar key={m.id} id={m.id} size="xs" />
          ))}
        </div>
      </div>

      {/* References */}
      {data.references.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1">
          {data.references.map((ref) => (
            <span
              key={ref}
              className="inline-flex items-center gap-0.5 rounded border border-border bg-secondary/50 px-1.5 py-0.2 font-mono text-[9px] text-muted-foreground"
            >
              <FileText className="size-2" />
              <span>{ref}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
