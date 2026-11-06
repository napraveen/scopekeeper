import { useState } from 'react'
import { CheckCircle2, Clock, Sparkles } from 'lucide-react'
import { Avatar } from '@/components/Avatar'
import { ConfirmPost } from '@/components/ConfirmPost'
import { SwitchTag } from '@/components/SwitchTag'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { api, qk } from '@/lib/api/client'
import { useChangeRequests } from '@/lib/api/queries'
import type { ChangeRequest } from '@/lib/api/types'
import { person } from '@/lib/people'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

export function NeedsAYes() {
  const queryClient = useQueryClient()
  const { data: changeRequests, isLoading } = useChangeRequests()
  const [confirmTarget, setConfirmTarget] = useState<{
    cr: ChangeRequest
    actionType: 'confirm' | 'approve'
    title: string
    message: string
  } | null>(null)

  if (isLoading) {
    return (
      <section aria-label="Decisions needing approval" className="rounded-2xl border border-border/80 glass-card p-5">
        <Skeleton className="h-6 w-36 mb-3" />
        <Skeleton className="h-24 w-full rounded-xl" />
      </section>
    )
  }

  // Filter change requests waiting on Ravi or Priya
  const pendingConfirmation = (changeRequests ?? []).filter((cr) => cr.status === 'awaiting_confirmation')
  const pendingApproval = (changeRequests ?? []).filter((cr) => cr.status === 'awaiting_approval')

  const totalWaiting = pendingConfirmation.length + pendingApproval.length

  const handleAction = async () => {
    if (!confirmTarget) return
    const { cr, actionType } = confirmTarget

    try {
      if (actionType === 'confirm') {
        // Confirmation by Ravi
        toast.success(`Confirmed hours for ${cr.id}`)
      } else {
        // Approval by Priya
        const allKeys = cr.options.map((o) => o.key)
        await api.approve(cr.id, allKeys.length > 0 ? allKeys : ['A', 'B', 'C', 'D'])
        toast.success(`Approved options for ${cr.id} and sent to client`)
      }
      void queryClient.invalidateQueries({ queryKey: qk.changeRequests })
      void queryClient.invalidateQueries({ queryKey: qk.overview() })
    } catch (e) {
      toast.error('Failed to post decision')
      console.error(e)
    }
  }

  return (
    <section
      aria-label="Decisions needing approval"
      className={cn(
        'rounded-2xl border transition-all duration-300 glass-card p-5 sm:p-6 shadow-sm',
        totalWaiting > 0 ? 'border-amber-500/40 shadow-[0_4px_25px_rgba(245,158,11,0.08)]' : 'border-border/80',
      )}
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex flex-wrap items-center gap-2.5">
          <h2 className="text-base font-bold tracking-tight text-foreground">Needs a yes</h2>
          <span className={cn(
            'tabular rounded-full px-2.5 py-0.5 font-mono text-xs font-bold transition-colors',
            totalWaiting > 0
              ? 'bg-amber-500/15 text-amber-800 dark:text-amber-200 ring-1 ring-amber-500/30'
              : 'bg-primary/10 text-primary',
          )}>
            {totalWaiting}
          </span>
          <SwitchTag kind="Role" label="Role · @delivery-lead / @account-manager" />
        </div>
        <span className="text-xs font-medium text-muted-foreground">
          Internal agency decisions required before client notification
        </span>
      </div>

      {totalWaiting === 0 ? (
        <div className="flex items-center gap-3 rounded-xl border border-dashed border-border/80 bg-secondary/20 p-4 text-xs font-medium text-muted-foreground">
          <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span>All clear! No decisions waiting on Priya or Ravi right now.</span>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Ravi awaiting confirmation */}
          {pendingConfirmation.map((cr) => {
            const who = person('ravi')
            return (
              <div
                key={cr.id}
                className="flex flex-col gap-3 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 sm:flex-row sm:items-center sm:justify-between transition-all hover:border-amber-500/50"
              >
                <div className="flex items-start gap-3.5">
                  <Avatar id="ravi" size="md" />
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-bold text-foreground">{who.name}</span>
                      <span className="rounded bg-secondary/80 px-1.5 py-0.2 font-mono text-[10px] font-semibold text-muted-foreground">
                        @delivery-lead
                      </span>
                      <span className="inline-flex items-center gap-1 font-mono text-xs font-bold text-primary">
                        <Clock className="size-3" />
                        {cr.id}
                      </span>
                    </div>
                    <p className="mt-1 text-xs font-semibold text-foreground">
                      Confirm baseline estimate of{' '}
                      <strong className="text-primary font-mono">{cr.estimate?.full.p50Hours ?? 190} h</strong>{' '}
                      (Ravi sizing to 200 h for Android app)
                    </p>
                    <p className="mt-0.5 text-[11px] text-muted-foreground">
                      P50/P90 medium confidence ({cr.estimate?.similar.length ?? 3} similar past PRs)
                    </p>
                  </div>
                </div>

                <div className="shrink-0 flex items-center gap-2">
                  <Button
                    type="button"
                    size="sm"
                    onClick={() =>
                      setConfirmTarget({
                        cr,
                        actionType: 'confirm',
                        title: `Confirm 200 h estimate for ${cr.id}`,
                        message: `@clerk CONFIRMED ${cr.id} hours=200 confidence=medium`,
                      })
                    }
                    className="gap-1.5 font-semibold text-xs h-9 px-4 shadow-xs"
                  >
                    <Sparkles className="size-3.5" />
                    <span>Confirm 200 h</span>
                  </Button>
                </div>
              </div>
            )
          })}

          {/* Priya awaiting approval */}
          {pendingApproval.map((cr) => {
            const who = person('priya')
            return (
              <div
                key={cr.id}
                className="flex flex-col gap-3 rounded-xl border border-primary/30 bg-primary/5 p-4 sm:flex-row sm:items-center sm:justify-between transition-all hover:border-primary/50"
              >
                <div className="flex items-start gap-3.5">
                  <Avatar id="priya" size="md" />
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-bold text-foreground">{who.name}</span>
                      <span className="rounded bg-secondary/80 px-1.5 py-0.2 font-mono text-[10px] font-semibold text-muted-foreground">
                        @account-manager
                      </span>
                      <span className="font-mono text-xs font-bold text-primary">{cr.id}</span>
                    </div>
                    <p className="mt-1 text-xs font-semibold text-foreground">
                      Approve 4 standardized client options (A, B, C, and D Scope Swap)
                    </p>
                    <p className="mt-0.5 text-[11px] text-muted-foreground">
                      Priced at $45/h + contingency · Option D swaps unstarted I9 (58h) for $0
                    </p>
                  </div>
                </div>

                <div className="shrink-0 flex items-center gap-2">
                  <Button
                    type="button"
                    size="sm"
                    onClick={() =>
                      setConfirmTarget({
                        cr,
                        actionType: 'approve',
                        title: `Approve Options A-D for ${cr.id}`,
                        message: `@scout SEND_OPTIONS ${cr.id} options=A,B,C,D`,
                      })
                    }
                    className="gap-1.5 font-semibold text-xs h-9 px-4 shadow-xs"
                  >
                    <span>Approve Options</span>
                  </Button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Confirm modal before posting */}
      {confirmTarget && (
        <ConfirmPost
          open={Boolean(confirmTarget)}
          onOpenChange={(open) => !open && setConfirmTarget(null)}
          title={confirmTarget.title}
          target={{ app: 'slack', room: 'acme-delivery', url: 'https://slack.com' }}
          message={confirmTarget.message}
          onConfirm={handleAction}
        />
      )}
    </section>
  )
}
