import { useState } from 'react'
import {
  ExternalLink,
  GitBranch,
  GitPullRequest,
  Globe,
  HeartHandshake,
  HelpCircle,
  Layers,
} from 'lucide-react'
import { useNavigate } from 'react-router'
import { Avatar } from '@/components/Avatar'
import { CategoryChip } from '@/components/CategoryChip'
import { ClauseBadge } from '@/components/ClauseBadge'
import { ChatLink } from '@/components/ChatLink'
import { ConfirmPost } from '@/components/ConfirmPost'
import { DualTime } from '@/components/DualTime'
import { SwitchTag } from '@/components/SwitchTag'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { qk } from '@/lib/api/client'
import { useAsk } from '@/lib/api/queries'
import { useQueryClient } from '@tanstack/react-query'
import { useUiStore } from '@/stores/ui'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

export function AskDrawer() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const activeAskId = useUiStore((s) => s.activeAskId)
  const setActiveAskId = useUiStore((s) => s.setActiveAskId)
  const { data: ask, isLoading } = useAsk(activeAskId)

  const [goodwillOpen, setGoodwillOpen] = useState(false)

  const open = Boolean(activeAskId)

  const handleGoodwillConfirm = async () => {
    if (!ask) return
    try {
      const res = await fetch(`/api/asks/${ask.id}/goodwill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hours: 2 }),
      })
      if (!res.ok) throw new Error('Goodwill call failed')
      toast.success(`Covered ${ask.id} with 2 h of goodwill from Priya.`)
      void queryClient.invalidateQueries({ queryKey: qk.ask(ask.id) })
      void queryClient.invalidateQueries({ queryKey: qk.asks })
      void queryClient.invalidateQueries({ queryKey: qk.overview() })
      void queryClient.invalidateQueries({ queryKey: qk.ledger() })
    } catch {
      toast.error('Failed to apply goodwill')
    }
  }

  return (
    <>
      <Sheet open={open} onOpenChange={(isOpen) => !isOpen && setActiveAskId(null)}>
        <SheetContent
          side="right"
          className="w-full sm:max-w-lg p-0 overflow-y-auto flex flex-col gap-0 border-l border-border/80 glass-card"
        >
          <SheetHeader className="p-5 border-b border-border/80 sticky top-0 bg-card/95 backdrop-blur-md z-10">
            <div className="flex items-center justify-between pr-6">
              <div className="flex items-center gap-2.5">
                <SheetTitle className="font-mono text-lg font-extrabold text-foreground tracking-tight">
                  {activeAskId}
                </SheetTitle>
                {ask?.category && <CategoryChip category={ask.category} size="xs" />}
              </div>
              {ask?.source && <ChatLink link={ask.source} variant="room" />}
            </div>
            <SheetDescription className="sr-only">
              Details, classification verdict, timeline, and work items for {activeAskId}
            </SheetDescription>
          </SheetHeader>

          {isLoading || !ask ? (
            <div className="p-6 space-y-4">
              <Skeleton className="h-24 w-full rounded-2xl" />
              <Skeleton className="h-36 w-full rounded-2xl" />
              <Skeleton className="h-48 w-full rounded-2xl" />
            </div>
          ) : (
            <div className="p-6 space-y-6">
              {/* The Quote in large type with Quote card styling */}
              <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-secondary/35 p-5 space-y-3 shadow-2xs">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Avatar id={ask.requester} size="sm" showName />
                    <span className="text-xs font-semibold text-muted-foreground">in #acme-client</span>
                  </div>
                  <DualTime iso={ask.createdAt} relative />
                </div>
                <blockquote className="text-base font-semibold text-foreground leading-snug">
                  “{ask.quote}”
                </blockquote>
                <div className="pt-1">
                  <ChatLink link={ask.source} variant="open" />
                </div>
              </div>

              {/* Contract Verdict */}
              <div className="rounded-2xl border border-border/80 bg-card/75 p-5 space-y-4 shadow-2xs">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Contract Verdict
                  </h4>
                  <SwitchTag kind="Agent · Custom" label="Agent · Clerk" />
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <CategoryChip category={ask.category} />
                  {ask.clauseIds.map((c) => (
                    <ClauseBadge key={c} clauseId={c} />
                  ))}
                </div>

                {typeof ask.confidence === 'number' && (
                  <div className="space-y-1.5 pt-1">
                    <div className="flex justify-between text-xs font-medium text-muted-foreground">
                      <span>Clerk contract classification confidence</span>
                      <span className="font-mono font-bold text-foreground">
                        {Math.round(ask.confidence * 100)}%
                      </span>
                    </div>
                    <div className="h-2 w-full bg-secondary rounded-full overflow-hidden p-0.5">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all duration-500',
                          ask.confidence >= 0.85 ? 'bg-emerald-500' : 'bg-primary',
                        )}
                        style={{ width: `${Math.round(ask.confidence * 100)}%` }}
                      />
                    </div>
                  </div>
                )}

                {ask.reason && (
                  <p className="text-xs text-foreground leading-relaxed pt-1">
                    <span className="font-bold text-foreground">SOW Rationale:</span> {ask.reason}
                  </p>
                )}

                {ask.decisionId && (
                  <div className="rounded-xl border border-primary/20 bg-primary/5 p-3 text-xs text-foreground space-y-1">
                    <span className="font-bold text-primary">Precedent Decision:</span>{' '}
                    <span className="font-mono font-bold">{ask.decisionId}</span> (Notifications are email-only; no SMS)
                  </div>
                )}

                {/* Goodwill CTA if out of scope and not part of an expensive change */}
                {ask.category === 'OUT_OF_SCOPE' && !ask.crId && ask.status !== 'accepted' && (
                  <div className="pt-2 border-t border-border/60">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setGoodwillOpen(true)}
                      className="gap-2 text-xs font-bold w-full h-9 border-amber-500/40 hover:bg-amber-500/10 hover:border-amber-500 text-foreground transition-all"
                    >
                      <HeartHandshake className="size-4 text-amber-500" />
                      <span>Cover with goodwill (2 h from 8 h bucket)</span>
                    </Button>
                  </div>
                )}
              </div>

              {/* Clarification Question if any */}
              {ask.question && (
                <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-amber-700 dark:text-amber-300">
                    <HelpCircle className="size-4" />
                    <span>Clarification Question</span>
                  </div>
                  <p className="text-xs text-foreground font-semibold leading-relaxed">{ask.question.text}</p>
                  {ask.question.answer ? (
                    <div className="rounded-xl border border-amber-500/20 bg-card/90 p-3 text-xs shadow-2xs">
                      <span className="text-muted-foreground font-medium">Client answer: </span>
                      <span className="font-bold text-foreground">“{ask.question.answer}”</span>
                    </div>
                  ) : (
                    <p className="text-xs text-amber-600/90 dark:text-amber-400/90 italic">
                      Waiting for client answer in #acme-client...
                    </p>
                  )}
                </div>
              )}

              {/* Linked Change Request & Work Items */}
              {(ask.crId || ask.workItems.length > 0) && (
                <div className="space-y-3.5">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Execution &amp; Live Previews
                  </h4>

                  {ask.crId && (
                    <button
                      type="button"
                      onClick={() => {
                        setActiveAskId(null)
                        navigate(`/change-requests/${ask.crId}`)
                      }}
                      className="w-full flex items-center justify-between rounded-xl border border-border/80 p-3.5 text-xs bg-card hover:border-primary/60 hover:shadow-sm transition-all text-left group"
                    >
                      <div className="flex items-center gap-2.5">
                        <div className="flex size-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
                          <Layers className="size-4" />
                        </div>
                        <div>
                          <div className="font-bold text-foreground group-hover:text-primary transition-colors">
                            Change Request {ask.crId}
                          </div>
                          <div className="text-[10px] text-muted-foreground">Click to inspect options &amp; timeline</div>
                        </div>
                      </div>
                      <span className="rounded-full bg-secondary border border-border/60 px-2.5 py-0.5 font-bold font-mono text-[10px] uppercase text-foreground flex items-center gap-1">
                        {ask.status.replace('_', ' ')}
                        <ExternalLink className="size-3 text-muted-foreground" />
                      </span>
                    </button>
                  )}

                  {ask.workItems.map((work) => (
                    <div
                      key={work.id}
                      className="rounded-xl border border-border/80 p-4 text-xs bg-card/95 space-y-2.5 shadow-2xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-foreground text-xs">{work.title}</span>
                        <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] uppercase font-mono font-bold text-muted-foreground">
                          {work.status}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 text-muted-foreground font-mono text-xs">
                        <GitBranch className="size-3.5 text-primary" />
                        <span className="font-semibold text-foreground">{work.branch}</span>
                      </div>

                      <div className="flex flex-wrap gap-4 pt-1 border-t border-border/60">
                        {work.prUrl && (
                          <a
                            href={work.prUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 text-primary font-bold hover:underline"
                          >
                            <GitPullRequest className="size-3.5" />
                            <span>View Pull Request #{work.id.replace(/\D/g, '') || '12'}</span>
                          </a>
                        )}
                        {work.previewUrl && (
                          <a
                            href={work.previewUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-bold hover:underline"
                          >
                            <Globe className="size-3.5" />
                            <span>Live Worktree Preview</span>
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Goodwill Confirmation Dialog */}
      {goodwillOpen && (
        <ConfirmPost
          open={goodwillOpen}
          onOpenChange={setGoodwillOpen}
          title={`Cover ${ask?.id} with Goodwill?`}
          target={{ app: 'slack', room: 'acme-intake', url: 'https://slack.com' }}
          message={`@clerk GOODWILL ${ask?.id} hours=2 approved_by=priya`}
          onConfirm={handleGoodwillConfirm}
        />
      )}
    </>
  )
}
