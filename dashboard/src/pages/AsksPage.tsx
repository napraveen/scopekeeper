import { useMemo, useState } from 'react'
import {
  ChevronRight,
  Search,
} from 'lucide-react'
import { Avatar } from '@/components/Avatar'
import { CategoryChip } from '@/components/CategoryChip'
import { ClauseBadge } from '@/components/ClauseBadge'
import { ChatLink } from '@/components/ChatLink'
import { DualTime } from '@/components/DualTime'
import { EmptyState } from '@/components/EmptyState'
import { SwitchTag } from '@/components/SwitchTag'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAsks } from '@/lib/api/queries'
import type { Category } from '@/lib/api/types'
import { CATEGORY, CATEGORY_ORDER } from '@/lib/categories'
import { useUiStore } from '@/stores/ui'
import { cn } from '@/lib/utils'

export function AsksPage() {
  const { data, isLoading } = useAsks()
  const setActiveAskId = useUiStore((s) => s.setActiveAskId)

  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<Category | 'ALL'>('ALL')
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL')
  const [viewPreset, setViewPreset] = useState<'all' | 'this_week' | 'out_of_scope' | 'active'>('all')

  const items = data?.items ?? []

  // Filter items
  const filtered = useMemo(() => {
    return items.filter((ask) => {
      // Preset filters
      if (viewPreset === 'this_week') {
        const d = new Date(ask.createdAt).getTime()
        const weekAgo = new Date('2026-11-01T00:00:00+05:30').getTime()
        if (d < weekAgo) return false
      } else if (viewPreset === 'out_of_scope') {
        if (ask.category !== 'OUT_OF_SCOPE') return false
      } else if (viewPreset === 'active') {
        if (ask.status === 'accepted' || ask.status === 'declined' || ask.status === 'invoiced') {
          return false
        }
      }

      // Category filter
      if (selectedCategory !== 'ALL' && ask.category !== selectedCategory) {
        return false
      }

      // Status filter
      if (selectedStatus !== 'ALL' && ask.status !== selectedStatus) {
        return false
      }

      // Search query (id or quote)
      if (search.trim()) {
        const q = search.toLowerCase()
        const matchesId = ask.id.toLowerCase().includes(q)
        const matchesQuote = ask.quote.toLowerCase().includes(q)
        const matchesCr = ask.crId?.toLowerCase().includes(q)
        if (!matchesId && !matchesQuote && !matchesCr) return false
      }

      return true
    })
  }, [items, search, selectedCategory, selectedStatus, viewPreset])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Asks</h1>
            <span className="tabular rounded-full bg-secondary px-2 py-0.5 font-mono text-xs font-semibold text-muted-foreground">
              {filtered.length} of {items.length}
            </span>
            <SwitchTag kind="Agent · Custom" label="Agent · Clerk (Contract Keeper)" />
          </div>
          <p className="text-xs text-muted-foreground">
            Complete registry of client asks classified against the signed Statement of Work.
          </p>
        </div>

        {/* View Presets */}
        <div className="flex items-center gap-1.5 rounded-lg border border-border bg-secondary/40 p-1">
          <button
            type="button"
            onClick={() => {
              setViewPreset('all')
              setSelectedCategory('ALL')
              setSelectedStatus('ALL')
            }}
            className={cn(
              'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
              viewPreset === 'all'
                ? 'bg-background font-semibold text-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            All asks
          </button>
          <button
            type="button"
            onClick={() => setViewPreset('this_week')}
            className={cn(
              'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
              viewPreset === 'this_week'
                ? 'bg-background font-semibold text-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            This week (Nov)
          </button>
          <button
            type="button"
            onClick={() => setViewPreset('out_of_scope')}
            className={cn(
              'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
              viewPreset === 'out_of_scope'
                ? 'bg-background font-semibold text-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            Out of scope
          </button>
          <button
            type="button"
            onClick={() => setViewPreset('active')}
            className={cn(
              'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
              viewPreset === 'active'
                ? 'bg-background font-semibold text-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            In-flight
          </button>
        </div>
      </div>

      {/* Filter toolbar */}
      <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" aria-hidden="true" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search ask ID, text, or CR-00N..."
            className="w-full rounded-lg border border-border bg-background pl-9 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-hidden"
          />
        </div>

        {/* Dropdowns */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Category filter */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-muted-foreground font-medium">Category:</span>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value as Category | 'ALL')}
              className="rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs font-medium text-foreground focus:border-primary focus:outline-hidden"
            >
              <option value="ALL">All categories</option>
              {CATEGORY_ORDER.map((c) => (
                <option key={c} value={c}>
                  {CATEGORY[c].label}
                </option>
              ))}
            </select>
          </div>

          {/* Status filter */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-muted-foreground font-medium">Status:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs font-medium text-foreground focus:border-primary focus:outline-hidden"
            >
              <option value="ALL">All statuses</option>
              <option value="received">Received</option>
              <option value="classified">Classified</option>
              <option value="ticketed">Ticketed</option>
              <option value="question_pending">Question pending</option>
              <option value="change_open">Change open</option>
              <option value="change_sent">Change sent</option>
              <option value="approved">Approved</option>
              <option value="swapped">Swapped</option>
              <option value="building">Building</option>
              <option value="preview">Preview ready</option>
              <option value="accepted">Accepted</option>
              <option value="declined">Declined</option>
            </select>
          </div>

          {(selectedCategory !== 'ALL' || selectedStatus !== 'ALL' || search.trim()) && (
            <Button
              type="button"
              variant="ghost"
              size="xs"
              onClick={() => {
                setSelectedCategory('ALL')
                setSelectedStatus('ALL')
                setSearch('')
              }}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Reset filters
            </Button>
          )}
        </div>
      </div>

      {/* Asks Table */}
      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
        {isLoading ? (
          <div className="p-6 space-y-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full rounded-lg" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No asks match your filter"
              description="Try adjusting your search criteria, category selection, or reset view presets."
              action={
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setViewPreset('all')
                    setSelectedCategory('ALL')
                    setSelectedStatus('ALL')
                    setSearch('')
                  }}
                >
                  Clear all filters
                </Button>
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <caption className="sr-only">Client asks classified against statement of work</caption>
              <thead>
                <tr className="border-b border-border bg-secondary/40 font-semibold text-muted-foreground">
                  <th scope="col" className="px-4 py-3 font-mono">ID</th>
                  <th scope="col" className="px-4 py-3">Quote</th>
                  <th scope="col" className="px-4 py-3">Requester</th>
                  <th scope="col" className="px-4 py-3">Category</th>
                  <th scope="col" className="px-4 py-3">SOW Clause</th>
                  <th scope="col" className="px-4 py-3">Status</th>
                  <th scope="col" className="px-4 py-3">Logged (Both Zones)</th>
                  <th scope="col" className="px-4 py-3 text-right">Channel</th>
                  <th scope="col" className="w-8 px-2 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {filtered.map((ask) => {
                  return (
                    <tr
                      key={ask.id}
                      onClick={() => setActiveAskId(ask.id)}
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          setActiveAskId(ask.id)
                        }
                      }}
                      className="group cursor-pointer hover:bg-accent/40 transition-colors focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      {/* ID */}
                      <td className="px-4 py-3 font-mono font-semibold text-foreground whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span>{ask.id}</span>
                          {ask.crId && (
                            <span className="rounded bg-primary/10 px-1 py-0.2 font-mono text-[10px] font-bold text-primary">
                              {ask.crId}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Quote */}
                      <td className="px-4 py-3 max-w-xs md:max-w-md font-medium text-foreground">
                        <span className="line-clamp-2">“{ask.quote}”</span>
                        {ask.reason && (
                          <span className="block mt-0.5 text-[11px] text-muted-foreground truncate font-normal">
                            {ask.reason}
                          </span>
                        )}
                      </td>

                      {/* Requester */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <Avatar id={ask.requester} size="xs" showName />
                      </td>

                      {/* Category */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <CategoryChip category={ask.category} size="xs" />
                      </td>

                      {/* Clause */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-1">
                          {ask.clauseIds.map((c) => (
                            <ClauseBadge key={c} clauseId={c} />
                          ))}
                          {ask.clauseIds.length === 0 && (
                            <span className="font-mono text-muted-foreground/60 text-[11px]">--</span>
                          )}
                        </div>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="inline-flex items-center rounded-md bg-secondary px-2 py-0.5 text-[11px] font-medium text-foreground capitalize">
                          {ask.status.replace('_', ' ')}
                        </span>
                      </td>

                      {/* Time in both zones */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <DualTime iso={ask.createdAt} className="text-xs" />
                      </td>

                      {/* Links */}
                      <td className="px-4 py-3 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        <ChatLink link={ask.source} variant="room" />
                      </td>

                      {/* Arrow */}
                      <td className="px-2 py-3 text-muted-foreground group-hover:text-foreground">
                        <ChevronRight className="size-4" />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
