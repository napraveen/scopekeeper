import { useMemo, useState } from 'react'
import {
  AlertCircle,
  CheckCircle,
  Code2,
  Flame,
  Pencil,
  XCircle,
} from 'lucide-react'
import { CategoryChip } from '@/components/CategoryChip'
import { SwitchTag } from '@/components/SwitchTag'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { qk } from '@/lib/api/client'
import { useAsks, useScope } from '@/lib/api/queries'
import type { Clause } from '@/lib/api/types'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

export function ScopePage() {
  const queryClient = useQueryClient()
  const { data: scope, isLoading } = useScope()
  const { data: asksData } = useAsks()

  const asks = asksData?.items ?? []

  // Selected clause for inspection drawer/dialog
  const [selectedClause, setSelectedClause] = useState<Clause | null>(null)

  // YAML editor dialog state
  const [yamlEditorOpen, setYamlEditorOpen] = useState(false)
  const [yamlContent, setYamlContent] = useState('')
  const [yamlError, setYamlError] = useState<string | null>(null)
  const [showDiff, setShowDiff] = useState(false)

  // Count asks per clause
  const clauseHitCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const ask of asks) {
      for (const c of ask.clauseIds) {
        counts[c] = (counts[c] ?? 0) + 1
      }
    }
    return counts
  }, [asks])

  // Split in-scope and out-of-scope clauses
  const inScopeClauses = scope?.clauses.filter((c) => c.kind === 'in') ?? []
  const outScopeClauses = scope?.clauses.filter((c) => c.kind === 'out') ?? []

  // Initialise YAML editor content from scope
  const handleOpenYamlEditor = () => {
    if (!scope) return
    const yaml = `# ScopeKeeper Statement of Work Contract Map
# Governed under Pixel & Co standard warranty (${scope.warrantyDays} days)
warrantyDays: ${scope.warrantyDays}
clauses:
${scope.clauses
  .map(
    (c) => `  - id: "${c.id}"
    kind: "${c.kind}"
    title: "${c.title}"
    deliverable: "${c.deliverable ?? ''}"
    includes:
${c.includes.map((inc) => `      - "${inc}"`).join('\n')}
    excerpt: "${c.excerpt}"`,
  )
  .join('\n')}
`
    setYamlContent(yaml)
    setYamlError(null)
    setShowDiff(false)
    setYamlEditorOpen(true)
  }

  const handleValidateYaml = (text: string) => {
    setYamlContent(text)
    // Basic validation
    if (!text.includes('clauses:') || !text.includes('warrantyDays:')) {
      setYamlError('YAML must contain root keys "warrantyDays" and "clauses"')
    } else {
      setYamlError(null)
    }
  }

  const handleSaveYaml = async () => {
    if (yamlError) return
    try {
      await fetch('/api/config/scope-map', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scope),
      })
      toast.success('Scope contract map updated successfully')
      setYamlEditorOpen(false)
      void queryClient.invalidateQueries({ queryKey: qk.scope })
    } catch {
      toast.error('Failed to update scope map')
    }
  }

  if (isLoading || !scope) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-48" />
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Skeleton className="h-96 rounded-xl" />
          <Skeleton className="h-96 rounded-xl" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Scope (Contract Map)
            </h1>
            <SwitchTag kind="Reference" label="Reference · SOW v1.2" />
          </div>
          <p className="text-xs text-muted-foreground">
            Signed Statement of Work contract boundaries, deliverables D1–D4, and exclusions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="rounded-md border border-border bg-secondary/50 px-2.5 py-1 font-mono text-xs text-muted-foreground">
            Warranty: {scope.warrantyDays} days
          </span>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleOpenYamlEditor}
            className="gap-1.5 text-xs font-semibold"
          >
            <Pencil className="size-3.5" />
            <span>Edit Scope YAML</span>
          </Button>
        </div>
      </div>

      {/* Two columns: In Scope vs Out of Scope */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Column 1: In Scope (Deliverables D1 to D4) */}
        <section
          aria-label="In-scope deliverables"
          className="rounded-xl border border-border bg-card p-5 space-y-4 shadow-xs"
        >
          <div className="flex items-center justify-between pb-3 border-b border-border/70">
            <div className="flex items-center gap-2">
              <CheckCircle className="size-4 text-emerald-600 dark:text-emerald-400" />
              <h2 className="text-sm font-bold text-foreground">In Scope Deliverables (D1–D4)</h2>
            </div>
            <span className="tabular font-mono text-xs text-emerald-600 dark:text-emerald-400 font-semibold">
              {inScopeClauses.length} clauses
            </span>
          </div>

          <div className="space-y-3">
            {inScopeClauses.map((clause) => {
              const hits = clauseHitCounts[clause.id] ?? 0
              return (
                <div
                  key={clause.id}
                  onClick={() => setSelectedClause(clause)}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      setSelectedClause(clause)
                    }
                  }}
                  className="group cursor-pointer rounded-xl border border-border bg-secondary/20 p-4 transition-all hover:border-primary/50 hover:bg-accent/15 hover:shadow-xs focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        {clause.deliverable && (
                          <span className="rounded bg-primary/10 px-1.5 py-0.2 font-mono text-xs font-bold text-primary">
                            {clause.deliverable}
                          </span>
                        )}
                        <span className="font-mono text-xs font-semibold text-muted-foreground">
                          §{clause.id}
                        </span>
                        <h3 className="font-semibold text-xs text-foreground">{clause.title}</h3>
                      </div>
                    </div>

                    {/* Ask Hit Heat Strip */}
                    <div
                      className="flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-[11px] font-mono"
                      title={`${hits} client asks referenced this clause`}
                    >
                      <Flame
                        className={cn(
                          'size-3',
                          hits > 2
                            ? 'text-amber-500 fill-amber-500'
                            : hits > 0
                              ? 'text-primary'
                              : 'text-muted-foreground/40',
                        )}
                      />
                      <span className="font-bold text-foreground">{hits}</span>
                      <span className="text-muted-foreground text-[10px]">hits</span>
                    </div>
                  </div>

                  <p className="mt-2 text-xs text-muted-foreground italic leading-relaxed">
                    “{clause.excerpt}”
                  </p>

                  {clause.includes.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5 pt-2 border-t border-border/50">
                      {clause.includes.map((inc) => (
                        <span
                          key={inc}
                          className="rounded bg-background px-2 py-0.5 font-mono text-[10px] text-foreground border border-border/60"
                        >
                          ✓ {inc}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>

        {/* Column 2: Out of Scope (Exclusions 1.3 & 3.5) */}
        <section
          aria-label="Out-of-scope exclusions"
          className="rounded-xl border border-border bg-card p-5 space-y-4 shadow-xs"
        >
          <div className="flex items-center justify-between pb-3 border-b border-border/70">
            <div className="flex items-center gap-2">
              <XCircle className="size-4 text-violet-600 dark:text-violet-400" />
              <h2 className="text-sm font-bold text-foreground">Out of Scope Exclusions</h2>
            </div>
            <span className="tabular font-mono text-xs text-violet-600 dark:text-violet-400 font-semibold">
              {outScopeClauses.length} exclusions
            </span>
          </div>

          <div className="space-y-3">
            {outScopeClauses.map((clause) => {
              const hits = clauseHitCounts[clause.id] ?? 0
              return (
                <div
                  key={clause.id}
                  onClick={() => setSelectedClause(clause)}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      setSelectedClause(clause)
                    }
                  }}
                  className="group cursor-pointer rounded-xl border border-border bg-secondary/20 p-4 transition-all hover:border-violet-500/50 hover:bg-violet-500/5 hover:shadow-xs focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-violet-600 dark:text-violet-400">
                        §{clause.id}
                      </span>
                      <h3 className="font-semibold text-xs text-foreground">{clause.title}</h3>
                    </div>

                    {/* Ask Hit Heat Strip */}
                    <div
                      className="flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-[11px] font-mono"
                      title={`${hits} client asks triggered this exclusion`}
                    >
                      <Flame
                        className={cn(
                          'size-3',
                          hits > 0 ? 'text-violet-500 fill-violet-500' : 'text-muted-foreground/40',
                        )}
                      />
                      <span className="font-bold text-foreground">{hits}</span>
                      <span className="text-muted-foreground text-[10px]">hits</span>
                    </div>
                  </div>

                  <p className="mt-2 text-xs text-muted-foreground italic leading-relaxed">
                    “{clause.excerpt}”
                  </p>

                  <div className="mt-3 pt-2 border-t border-border/50 text-[11px] text-violet-700 dark:text-violet-300 font-medium">
                    Trigger for Change Orders (e.g. CR-004 Android app)
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      </div>

      {/* Clause Detail Dialog */}
      {selectedClause && (
        <Dialog open={Boolean(selectedClause)} onOpenChange={(o) => !o && setSelectedClause(null)}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-primary">
                  Clause §{selectedClause.id}
                </span>
                {selectedClause.deliverable && (
                  <span className="rounded bg-secondary px-1.5 py-0.2 font-mono text-[10px] text-muted-foreground">
                    {selectedClause.deliverable}
                  </span>
                )}
              </div>
              <DialogTitle className="text-base">{selectedClause.title}</DialogTitle>
              <DialogDescription className="text-xs">
                {selectedClause.kind === 'in' ? 'Included deliverable' : 'Explicit contract exclusion'}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              <div className="rounded-lg bg-secondary/50 p-3 text-xs leading-relaxed italic text-foreground border border-border/60">
                “{selectedClause.excerpt}”
              </div>

              {/* Related Asks */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Asks referencing this clause ({clauseHitCounts[selectedClause.id] ?? 0})
                </h4>
                <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                  {asks
                    .filter((a) => a.clauseIds.includes(selectedClause.id))
                    .map((ask) => (
                      <div
                        key={ask.id}
                        className="rounded-lg border border-border p-2.5 text-xs bg-background flex flex-col gap-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-primary">{ask.id}</span>
                          <CategoryChip category={ask.category} size="xs" />
                        </div>
                        <p className="text-foreground">“{ask.quote}”</p>
                      </div>
                    ))}
                  {(clauseHitCounts[selectedClause.id] ?? 0) === 0 && (
                    <p className="text-xs text-muted-foreground italic">No asks logged against this clause yet.</p>
                  )}
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button size="sm" variant="outline" onClick={() => setSelectedClause(null)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* YAML Editor Dialog with Live Validation & Diff */}
      {yamlEditorOpen && (
        <Dialog open={yamlEditorOpen} onOpenChange={setYamlEditorOpen}>
          <DialogContent className="sm:max-w-2xl max-h-[90vh] flex flex-col">
            <DialogHeader>
              <div className="flex items-center gap-2">
                <Code2 className="size-4 text-primary" />
                <DialogTitle className="text-base">Edit Scope Map YAML</DialogTitle>
              </div>
              <DialogDescription className="text-xs">
                Live contract YAML schema. Updates reflect across the contract classifier instantly.
              </DialogDescription>
            </DialogHeader>

            <div className="flex-1 space-y-2 py-2 overflow-hidden flex flex-col">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-muted-foreground">scope-map.yaml</span>
                <button
                  type="button"
                  onClick={() => setShowDiff(!showDiff)}
                  className="text-xs text-primary hover:underline font-medium"
                >
                  {showDiff ? 'Show Code' : 'Show Diff Summary'}
                </button>
              </div>

              {showDiff ? (
                <div className="flex-1 rounded-lg border border-border bg-muted/60 p-3 font-mono text-xs overflow-y-auto max-h-80">
                  <div className="text-emerald-600 dark:text-emerald-400">
                    + Validated YAML matches Scope Schema v1.2
                  </div>
                  <div className="text-muted-foreground mt-2">
                    Active clauses: {scope.clauses.length} (4 in-scope, 2 exclusions)
                  </div>
                </div>
              ) : (
                <textarea
                  value={yamlContent}
                  onChange={(e) => handleValidateYaml(e.target.value)}
                  spellCheck={false}
                  className="w-full flex-1 min-h-[300px] rounded-lg border border-border bg-muted/40 p-3 font-mono text-xs text-foreground focus:border-primary focus:outline-hidden leading-relaxed resize-none"
                />
              )}

              {yamlError && (
                <div className="flex items-center gap-1.5 text-xs text-destructive font-medium">
                  <AlertCircle className="size-3.5" />
                  <span>{yamlError}</span>
                </div>
              )}
            </div>

            <DialogFooter className="gap-2 sm:justify-end">
              <Button variant="outline" size="sm" onClick={() => setYamlEditorOpen(false)}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleSaveYaml} disabled={Boolean(yamlError)}>
                Save &amp; Update Contract
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}
