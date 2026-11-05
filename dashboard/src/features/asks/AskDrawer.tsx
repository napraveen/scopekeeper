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
import { person } from '@/lib/people'
import { useQueryClient } from '@tanstack/react-query'
import { useUiStore } from '@/stores/ui'
import { toast } from 'sonner'

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
          className="w-full sm:max-w-lg p-0 overflow-y-auto flex flex-col gap-0 border-l border-border bg-card"
        >
          <SheetHeader className="p-5 border-b border-border/80 sticky top-0 bg-card/95 backdrop-blur z-10">
            <div className="flex items-center justify-between pr-6">
              <div className="flex items-center gap-2">
                <SheetTitle className="font-mono text-base font-bold text-foreground">
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
            <div className="p-5 space-y-4">
              <Skeleton className="h-20 w-full rounded-xl" />
              <Skeleton className="h-32 w-full rounded-xl" />
              <Skeleton className="h-44 w-full rounded-xl" />
            </div>
          ) : (
            <div className="p-5 space-y-6">
              {/* The Quote in large type */}
              <div className="rounded-xl border border-border bg-secondary/25 p-4 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Avatar id={ask.requester} size="sm" showName />
                    <span className="text-xs text-muted-foreground">in #acme-client</span>
                  </div>
                  <DualTime iso={ask.createdAt} relative />
                </div>
                <blockquote className="text-base font-medium text-foreground leading-snug">
                  “{ask.quote}”
                </blockquote>
                <div className="pt-1">
                  <ChatLink link={ask.source} variant="open" />
                </div>
              </div>

              {/* Verdict */}
              <div className="rounded-xl border border-border bg-secondary/15 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
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
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-muted-foreground">
                      <span>Clerk classification confidence</span>
                      <span className="font-mono font-medium text-foreground">
                        {Math.round(ask.confidence * 100)}%
                      </span>
                    </div>
                    <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full"
                        style={{ width: `${Math.round(ask.confidence * 100)}%` }}
                      />
                    </div>
                  </div>
                )}

                {ask.reason && (
                  <p className="text-xs text-foreground leading-relaxed">
                    <span className="font-semibold">Reason:</span> {ask.reason}
                  </p>
                )}

                {ask.decisionId && (
                  <div className="rounded-lg border border-border/80 bg-background/80 p-2.5 text-xs text-muted-foreground">
                    <span className="font-semibold text-foreground">Governing decision:</span>{' '}
                    <span className="font-mono text-primary font-medium">{ask.decisionId}</span> (Notifications are email-only; no SMS)
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
                      className="gap-1.5 text-xs font-medium w-full"
                    >
                      <HeartHandshake className="size-3.5 text-primary" />
                      <span>Cover with goodwill (2 h from 8 h bucket)</span>
                    </Button>
                  </div>
                )}
              </div>

              {/* Clarification Question if any */}
              {ask.question && (
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-amber-600 dark:text-amber-400">
                    <HelpCircle className="size-4" />
                    <span>Clarification Question</span>
                  </div>
                  <p className="text-xs text-foreground font-medium">{ask.question.text}</p>
                  {ask.question.answer ? (
                    <div className="rounded border border-amber-500/20 bg-background p-2 text-xs">
                      <span className="text-muted-foreground">Client answer: </span>
                      <span className="font-semibold text-foreground">{ask.question.answer}</span>
                    </div>
                  ) : (
                    <p className="text-[11px] text-amber-600/80 dark:text-amber-400/80">
                      Waiting for client answer in #acme-client...
                    </p>
                  )}
                </div>
              )}

              {/* Linked Change Request & Work Items */}
              {(ask.crId || ask.workItems.length > 0) && (
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Execution &amp; Previews
                  </h4>

                  {ask.crId && (
                    <button
                      type="button"
                      onClick={() => {
                        setActiveAskId(null)
                        navigate(`/change-requests/${ask.crId}`)
                      }}
                      className="w-full flex items-center justify-between rounded-lg border border-border p-3 text-xs bg-background hover:border-primary/60 transition-colors text-left"
                    >
                      <div className="flex items-center gap-2">
                        <Layers className="size-4 text-primary" />
                        <span className="font-semibold text-foreground">Change Request</span>
                        <span className="font-mono font-medium text-primary">{ask.crId}</span>
                      </div>
                      <span className="rounded bg-secondary px-2 py-0.5 font-medium capitalize text-foreground flex items-center gap-1">
                        {ask.status.replace('_', ' ')}
                        <ExternalLink className="size-3 text-muted-foreground" />
                      </span>
                    </button>
                  )}

                  {ask.workItems.map((work) => (
                    <div
                      key={work.id}
                      className="rounded-lg border border-border p-3 text-xs bg-background space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-foreground">{work.title}</span>
                        <span className="rounded bg-secondary px-2 py-0.5 text-[10px] uppercase font-mono text-muted-foreground">
                          {work.status}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 text-muted-foreground font-mono text-[11px]">
                        <GitBranch className="size-3 text-primary" />
                        <span>{work.branch}</span>
                      </div>

                      <div className="flex flex-wrap gap-3 pt-1">
                        {work.prUrl && (
                          <a
                            href={work.prUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-primary hover:underline"
                          >
                            <GitPullRequest className="size-3" />
                            <span>View Pull Request</span>
                            <ExternalLink className="size-2.5" />
                          </a>
                        )}
                        {work.previewUrl && (
                          <a
                            href={work.previewUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium hover:underline"
                          >
                            <Globe className="size-3" />
                            <span>Live Preview Ready</span>
                            <ExternalLink className="size-2.5" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Vertical timeline of events */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Ask Timeline
                </h4>

                <div className="relative border-l-2 border-border/80 ml-3 space-y-4 pl-4 pb-2">
                  {ask.events.map((ev) => (
                    <div key={ev.id} className="relative group text-xs">
                      <div className="absolute -left-[21px] top-1 size-2 rounded-full bg-primary ring-4 ring-card" />
                      <div className="flex flex-wrap items-baseline justify-between gap-1">
                        <div className="flex items-center gap-1.5 font-semibold text-foreground">
                          <Avatar id={ev.actor} size="xs" />
                          <span>{person(ev.actor).name}</span>
                        </div>
                        <DualTime iso={ev.ts} className="text-[11px]" />
                      </div>
                      <p className="mt-1 text-foreground leading-relaxed">{ev.text}</p>
                      {ev.link && (
                        <div className="mt-1">
                          <ChatLink link={ev.link} variant="open" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {goodwillOpen && ask && (
        <ConfirmPost
          open={goodwillOpen}
          onOpenChange={setGoodwillOpen}
          title="Cover with Goodwill"
          target={{ app: 'slack', room: 'acme-intake', url: 'https://pixelco.slack.com/archives/acme-intake' }}
          message={`Priya: I am covering ${ask.id} ("${ask.quote}") with 2 hours from our monthly goodwill bucket. No charge to Acme.`}
          confirmLabel="Apply goodwill"
          onConfirm={handleGoodwillConfirm}
        />
      )}
    </>
  )
}
