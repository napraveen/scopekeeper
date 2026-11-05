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
}

export const PIPELINE_STAGES: PipelineStage[] = [
  { id: 'received', label: 'Received' },
  { id: 'sorted', label: 'Sorted' },
  { id: 'waiting', label: 'Waiting on client' },
  { id: 'change_path', label: 'Change path' },
  { id: 'building', label: 'Building' },
  { id: 'preview', label: 'Preview' },
  { id: 'accepted', label: 'Accepted' },
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
      initial={reduceMotion ? false : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduceMotion ? undefined : { opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      key={`${ask.id}-${pulseCount > 0 ? 'pulsed' : 'init'}`}
      type="button"
      onClick={() => setActiveAskId(ask.id)}
      className={cn(
        'group w-full rounded-xl border border-border bg-background p-3 text-left transition-colors hover:border-primary/50 hover:bg-accent/25 focus-visible:outline-2 focus-visible:outline-ring',
        pulseCount > 0 && 'animate-glow',
      )}
    >
      <div className="flex items-center justify-between gap-1.5">
        <span className="font-mono text-xs font-semibold text-foreground">{ask.id}</span>
        {ask.crId && (
          <span className="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-primary">
            {ask.crId}
          </span>
        )}
      </div>

      <p className="mt-1.5 line-clamp-1 text-xs font-medium text-foreground" title={ask.quote}>
        “{ask.quote}”
      </p>

      <div className="mt-2 flex flex-wrap items-center gap-1">
        <CategoryChip category={ask.category} size="xs" />
        {ask.clauseIds.map((c) => (
          <ClauseBadge key={c} clauseId={c} />
        ))}
      </div>

      <div className="mt-2.5 flex items-center justify-between gap-2 border-t border-border/70 pt-2">
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
      <section aria-label="Live ask pipeline" className="rounded-xl border border-border bg-card p-4">
        <div className="mb-3 flex items-center justify-between">
          <Skeleton className="h-5 w-36" />
          <Skeleton className="h-4 w-24" />
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4 xl:grid-cols-7">
          {Array.from({ length: 7 }).map((_, i) => (
            <Skeleton key={i} className="h-56 rounded-xl" />
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
    <section aria-label="Live ask pipeline" className="rounded-xl border border-border bg-card p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-base font-semibold text-foreground">Live pipeline</h2>
          <SwitchTag kind="Agent · Custom" label="Agent · Clerk (SOW check)" />
          <SwitchTag kind="Reference" label="Reference · SOW v1.2" />
        </div>
        <span className="text-xs text-muted-foreground">
          Click any ask to inspect its clause &amp; chat thread
        </span>
      </div>

      {totalActive === 0 ? (
        <EmptyState
          title="No asks yet"
          description="When a client asks for something in chat, it appears here within a minute."
        />
      ) : (
        <LayoutGroup>
          {/* Desktop / tablet multi-column board, vertical stack on mobile (§6) */}
          <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2 lg:grid-cols-4 2xl:grid-cols-7">
            {PIPELINE_STAGES.map((stage) => {
              const stageItems = byStage[stage.id]
              return (
                <div
                  key={stage.id}
                  data-stage={stage.id}
                  className={cn(
                    'flex flex-col rounded-xl border border-border/80 bg-secondary/35 p-2.5',
                    stageItems.length === 0 && 'hidden md:flex',
                  )}
                >
                  <div className="mb-2 flex items-center justify-between gap-1 px-0.5">
                    <h3 className="text-xs font-semibold text-foreground">{stage.label}</h3>
                    <span className="tabular rounded-full bg-secondary px-1.5 py-0.5 font-mono text-[11px] font-medium text-muted-foreground">
                      {stageItems.length}
                    </span>
                  </div>

                  <div className="flex flex-1 flex-col gap-2">
                    <AnimatePresence initial={false}>
                      {stageItems.map((ask) => (
                        <AskPipelineCard key={ask.id} ask={ask} />
                      ))}
                    </AnimatePresence>
                    {stageItems.length === 0 && (
                      <div className="flex min-h-20 flex-1 items-center justify-center rounded-lg border border-dashed border-border/60 p-2 text-center text-[11px] text-muted-foreground">
                        Empty
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
