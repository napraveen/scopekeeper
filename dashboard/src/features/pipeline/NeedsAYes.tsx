import { useState } from 'react'
import { AlertCircle, CheckCircle2, Clock } from 'lucide-react'
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
      <section aria-label="Decisions needing approval" className="rounded-xl border border-border bg-card p-4">
        <Skeleton className="h-5 w-32 mb-3" />
        <Skeleton className="h-20 w-full rounded-xl" />
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
    <section aria-label="Decisions needing approval" className="rounded-xl border border-border bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-base font-semibold text-foreground">Needs a yes</h2>
          <span className="tabular rounded-full bg-primary/10 px-2 py-0.5 font-mono text-xs font-semibold text-primary">
            {totalWaiting}
          </span>
          <SwitchTag kind="Role" label="Role · @delivery-lead / @account-manager" />
        </div>
        <span className="text-xs text-muted-foreground">Internal agency decisions required to proceed</span>
      </div>

      {totalWaiting === 0 ? (
        <div className="flex items-center gap-3 rounded-lg border border-dashed border-border/80 bg-secondary/20 p-4 text-xs text-muted-foreground">
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
                className="flex flex-col gap-3 rounded-xl border border-border bg-secondary/30 p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-start gap-3">
                  <Avatar id="ravi" size="md" />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-foreground">{who.name}</span>
                      <span className="rounded bg-secondary px-1.5 py-0.2 font-mono text-[10px] text-muted-foreground">
                        @delivery-lead
                      </span>
                      <span className="inline-flex items-center gap-1 font-mono text-xs text-primary font-medium">
                        <Clock className="size-3" />
                        {cr.id}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-foreground font-medium">
                      Review &amp; confirm estimate for <span className="font-semibold">{cr.title}</span> (P50 190 h, P90 240 h)
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      Outside auto-envelope: over $500 and moves milestone M2
                    </p>
                  </div>
                </div>

                <Button
                  size="sm"
                  variant="default"
                  onClick={() =>
                    setConfirmTarget({
                      cr,
                      actionType: 'confirm',
                      title: `Confirm 200 h for ${cr.id}`,
                      message: `Ravi: I reviewed the estimate from Claude Code for ${cr.title}. Confirming 200 h based on similar historical changes. Ready for pricing.`,
                    })
                  }
                  className="shrink-0 font-medium"
                >
                  Confirm 200 h
                </Button>
              </div>
            )
          })}

          {/* Priya awaiting approval */}
          {pendingApproval.map((cr) => {
            const who = person('priya')
            return (
              <div
                key={cr.id}
                className="flex flex-col gap-3 rounded-xl border border-border bg-secondary/30 p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-start gap-3">
                  <Avatar id="priya" size="md" />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-foreground">{who.name}</span>
                      <span className="rounded bg-secondary px-1.5 py-0.2 font-mono text-[10px] text-muted-foreground">
                        @account-manager
                      </span>
                      <span className="inline-flex items-center gap-1 font-mono text-xs text-primary font-medium">
                        <AlertCircle className="size-3" />
                        {cr.id}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-foreground font-medium">
                      Approve client options A–D for <span className="font-semibold">{cr.title}</span> to send change order
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      Includes Option D (Swap with I9 admin analytics dashboard for $0)
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    size="sm"
                    variant="default"
                    onClick={() =>
                      setConfirmTarget({
                        cr,
                        actionType: 'approve',
                        title: `Approve CR-004 options A–D`,
                        message: `Priya: Approved options A, B, C, D for ${cr.id} (${cr.title}). Sending change order to Sam in #acme-client.`,
                      })
                    }
                    className="font-medium"
                  >
                    Approve all options
                  </Button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {confirmTarget && (
        <ConfirmPost
          open={Boolean(confirmTarget)}
          onOpenChange={(open) => !open && setConfirmTarget(null)}
          title={confirmTarget.title}
          target={confirmTarget.cr.room}
          message={confirmTarget.message}
          confirmLabel="Post approval"
          onConfirm={handleAction}
        />
      )}
    </section>
  )
}
