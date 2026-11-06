import { AnimatePresence, LayoutGroup, motion, useReducedMotion } from 'motion/react'
import { Avatar } from '@/components/Avatar'
import { CategoryChip } from '@/components/CategoryChip'
import { ClauseBadge } from '@/components/ClauseBadge'
import { DualTime } from '@/components/DualTime'
import { EmptyState } from '@/components/EmptyState'
import { SwitchTag } from '@/components/SwitchTag'
import { Skeleton } from '@/components/ui/skeleton'
import { useAsks } from '@/lib/api/queries'
import type { Ask, AskStatus } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { usePulseStore, useUiStore } from '@/stores/ui'

export type PipelineStageId =
  | 'received'
  | 'sorted'
  | 'waiting'
  | 'change_path'
  | 'building'
  | 'preview'
  | 'accepted'

export interface PipelineStage {
  id: PipelineStageId
  label: string
  color: string
}

export const PIPELINE_STAGES: PipelineStage[] = [
  { id: 'received', label: 'Received', color: 'bg-zinc-400' },
  { id: 'sorted', label: 'Sorted', color: 'bg-indigo-500' },
  { id: 'waiting', label: 'Waiting on client', color: 'bg-amber-500' },
  { id: 'change_path', label: 'Change path', color: 'bg-violet-500' },
  { id: 'building', label: 'Building', color: 'bg-blue-500' },
  { id: 'preview', label: 'Preview', color: 'bg-teal-500' },
  { id: 'accepted', label: 'Accepted', color: 'bg-emerald-500' },
]

export function mapStatusToStage(status: AskStatus): PipelineStageId | null {
  switch (status) {
    case 'received':
      return 'received'
    case 'classified':
    case 'ticketed':
    case 'linked':
      return 'sorted'
    case 'question_pending':
    case 'reminded':
      return 'waiting'
    case 'change_open':
    case 'change_sent':
    case 'approved':
    case 'swapped':
      return 'change_path'
    case 'building':
      return 'building'
    case 'preview':
      return 'preview'
    case 'accepted':
    case 'invoiced':
      return 'accepted'
    case 'declined':
      return null
  }
}

function AskPipelineCard({ ask }: { ask: Ask }) {
  const pulseCount = usePulseStore((s) => s.asks[ask.id] ?? 0)
  const setActiveAskId = useUiStore((s) => s.setActiveAskId)
  const reduceMotion = useReducedMotion()

  return (
    <motion.button
      layout={!reduceMotion}
      layoutId={reduceMotion ? undefined : `ask-card-${ask.id}`}
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduceMotion ? undefined : { opacity: 0, scale: 0.96 }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
      key={`${ask.id}-${pulseCount > 0 ? 'pulsed' : 'init'}`}
      type="button"
      onClick={() => setActiveAskId(ask.id)}
      className={cn(
        'group relative w-full rounded-xl border border-border/75 bg-card/95 p-3.5 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-md hover:bg-card focus-visible:outline-2 focus-visible:outline-ring',
        pulseCount > 0 && 'animate-glow ring-2 ring-primary/60 shadow-lg',
      )}
    >
      <div className="flex items-center justify-between gap-1.5">
        <span className="font-mono text-xs font-bold text-foreground group-hover:text-primary transition-colors">
          {ask.id}
        </span>
        {ask.crId && (
          <span className="rounded-md bg-primary/10 px-1.5 py-0.5 font-mono text-[10px] font-bold text-primary ring-1 ring-primary/20">
            {ask.crId}
          </span>
        )}
      </div>

      <p className="mt-1.5 line-clamp-2 text-xs font-medium text-foreground leading-snug group-hover:text-foreground" title={ask.quote}>
        “{ask.quote}”
      </p>

      <div className="mt-2.5 flex flex-wrap items-center gap-1">
        <CategoryChip category={ask.category} size="xs" />
        {ask.clauseIds.map((c) => (
          <ClauseBadge key={c} clauseId={c} />
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between gap-2 border-t border-border/60 pt-2 text-muted-foreground">
        <Avatar id={ask.requester} size="xs" showName />
        <DualTime iso={ask.createdAt} className="text-[11px]" />
      </div>
    </motion.button>
  )
}

export function LivePipeline() {
  const { data, isLoading } = useAsks()
  const items = data?.items ?? []

  if (isLoading) {
    return (
      <section aria-label="Live ask pipeline" className="rounded-2xl border border-border/80 glass-card p-5">
        <div className="mb-4 flex items-center justify-between">
          <Skeleton className="h-6 w-44" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="grid grid-cols-1 gap-3.5 md:grid-cols-4 xl:grid-cols-7">
          {Array.from({ length: 7 }).map((_, i) => (
            <Skeleton key={i} className="h-64 rounded-xl" />
          ))}
        </div>
      </section>
    )
  }

  const byStage: Record<PipelineStageId, Ask[]> = {
    received: [],
    sorted: [],
    waiting: [],
    change_path: [],
    building: [],
    preview: [],
    accepted: [],
  }

  for (const ask of items) {
    const stage = mapStatusToStage(ask.status)
    if (stage) byStage[stage].push(ask)
  }

  const totalActive = Object.values(byStage).reduce((sum, list) => sum + list.length, 0)

  return (
    <section aria-label="Live ask pipeline" className="rounded-2xl border border-border/80 glass-card p-5 sm:p-6 shadow-sm">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold tracking-tight text-foreground">Live Pipeline</h2>
            <span className="tabular rounded-full bg-primary/10 px-2 py-0.5 font-mono text-xs font-bold text-primary">
              {totalActive} in flight
            </span>
          </div>
          <SwitchTag kind="Agent · Custom" label="Agent · Clerk (SOW check)" />
          <SwitchTag kind="Reference" label="Reference · SOW v1.2" />
        </div>
        <span className="text-xs font-medium text-muted-foreground">
          Click any card to inspect contract clause, quote &amp; chat thread
        </span>
      </div>

      {totalActive === 0 ? (
        <EmptyState
          title="No asks yet"
          description="When a client asks for something in chat, it appears here within a minute."
        />
      ) : (
        <LayoutGroup>
          {/* Multi-column Kanban board */}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4 2xl:grid-cols-7">
            {PIPELINE_STAGES.map((stage) => {
              const stageItems = byStage[stage.id]
              return (
                <div
                  key={stage.id}
                  data-stage={stage.id}
                  className={cn(
                    'flex flex-col rounded-xl border border-border/70 bg-secondary/30 p-3 transition-colors',
                    stageItems.length === 0 && 'hidden md:flex',
                  )}
                >
                  <div className="mb-2.5 flex items-center justify-between gap-1.5 px-0.5">
                    <div className="flex items-center gap-1.5">
                      <span className={cn('size-2 rounded-full', stage.color)} />
                      <h3 className="text-xs font-bold text-foreground">{stage.label}</h3>
                    </div>
                    <span className="tabular rounded-full bg-secondary/80 border border-border/50 px-2 py-0.2 font-mono text-[11px] font-bold text-foreground">
                      {stageItems.length}
                    </span>
                  </div>

                  <div className="flex flex-1 flex-col gap-2.5 min-h-24">
                    <AnimatePresence initial={false}>
                      {stageItems.map((ask) => (
                        <AskPipelineCard key={ask.id} ask={ask} />
                      ))}
                    </AnimatePresence>
                    {stageItems.length === 0 && (
                      <div className="flex min-h-24 flex-1 items-center justify-center rounded-lg border border-dashed border-border/50 p-2 text-center text-xs font-medium text-muted-foreground/60 select-none">
                        No active items
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </LayoutGroup>
      )}
    </section>
  )
}
