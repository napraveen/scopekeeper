import { useMemo, useState } from 'react'
import { ChevronDown, ChevronRight, Radio } from 'lucide-react'
import { Avatar } from '@/components/Avatar'
import { ChatLink } from '@/components/ChatLink'
import { DualTime } from '@/components/DualTime'
import { SwitchTag } from '@/components/SwitchTag'
import { Skeleton } from '@/components/ui/skeleton'
import { useEvents } from '@/lib/api/queries'
import type { StreamEvent } from '@/lib/api/types'
import { person } from '@/lib/people'

interface GroupedEvent {
  id: string
  isGroup: boolean
  groupId?: string
  actor: string
  title: string
  events: StreamEvent[]
  ts: string
  link?: StreamEvent['link']
}

export function ActivityFeed() {
  const { data: events, isLoading } = useEvents()
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({})

  const toggleGroup = (groupId: string) => {
    setExpandedGroups((prev) => ({ ...prev, [groupId]: !prev[groupId] }))
  }

  const items = useMemo(() => {
    if (!events) return []

    const list: GroupedEvent[] = []
    let currentGroup: { id: string; events: StreamEvent[] } | null = null

    for (const ev of events) {
      const gId = (ev.data as { group?: string } | undefined)?.group

      if (gId) {
        if (currentGroup && currentGroup.id === gId) {
          currentGroup.events.push(ev)
          continue
        } else {
          if (currentGroup && currentGroup.events.length > 0) {
            const first = currentGroup.events[0]!
            const count = currentGroup.events.length
            const isSort = currentGroup.id.startsWith('sort')
            const summary = isSort
              ? `${person(first.actor).name} sorted ${count} asks`
              : `${person(first.actor).name} logged ${count} asks from Sam`

            list.push({
              id: currentGroup.id,
              isGroup: true,
              groupId: currentGroup.id,
              actor: first.actor,
              title: summary,
              events: currentGroup.events,
              ts: first.ts,
              link: first.link,
            })
          }
          currentGroup = { id: gId, events: [ev] }
        }
      } else {
        if (currentGroup && currentGroup.events.length > 0) {
          const first = currentGroup.events[0]!
          const count = currentGroup.events.length
          const isSort = currentGroup.id.startsWith('sort')
          const summary = isSort
            ? `${person(first.actor).name} sorted ${count} asks`
            : `${person(first.actor).name} logged ${count} asks from Sam`

          list.push({
            id: currentGroup.id,
            isGroup: true,
            groupId: currentGroup.id,
            actor: first.actor,
            title: summary,
            events: currentGroup.events,
            ts: first.ts,
            link: first.link,
          })
          currentGroup = null
        }

        list.push({
          id: ev.id,
          isGroup: false,
          actor: ev.actor,
          title: ev.text,
          events: [ev],
          ts: ev.ts,
          link: ev.link,
        })
      }
    }

    if (currentGroup && currentGroup.events.length > 0) {
      const first = currentGroup.events[0]!
      const count = currentGroup.events.length
      const isSort = currentGroup.id.startsWith('sort')
      const summary = isSort
        ? `${person(first.actor).name} sorted ${count} asks`
        : `${person(first.actor).name} logged ${count} asks from Sam`

      list.push({
        id: currentGroup.id,
        isGroup: true,
        groupId: currentGroup.id,
        actor: first.actor,
        title: summary,
        events: currentGroup.events,
        ts: first.ts,
        link: first.link,
      })
    }

    return list
  }, [events])

  if (isLoading) {
    return (
      <aside aria-label="Live activity feed" className="rounded-xl border border-border bg-card p-4">
        <Skeleton className="h-5 w-32 mb-3" />
        <div className="space-y-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex gap-2.5">
              <Skeleton className="size-7 rounded-full shrink-0" />
              <div className="space-y-1.5 flex-1">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            </div>
          ))}
        </div>
      </aside>
    )
  }

  // Text for aria-live announce
  const newestEventText = items[0]?.title ?? ''

  return (
    <aside
      aria-label="Live activity feed"
      className="flex flex-col rounded-xl border border-border bg-card p-4 h-full"
    >
      <div className="mb-3 flex items-center justify-between pb-2 border-b border-border/60">
        <div className="flex items-center gap-2">
          <Radio className="size-3.5 text-emerald-500 animate-pulse" aria-hidden="true" />
          <h2 className="text-base font-semibold text-foreground">Activity feed</h2>
          <SwitchTag kind="Room link" label="Switch stream" />
        </div>
        <span className="tabular font-mono text-xs text-muted-foreground">
          {items.length} items
        </span>
      </div>

      {/* Screen reader polite announcement of live stream updates */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {newestEventText}
      </div>

      <div className="flex-1 overflow-y-auto space-y-3.5 pr-1 max-h-[780px] scrollbar-thin">
        {items.length === 0 ? (
          <div className="p-4 text-center text-xs text-muted-foreground">
            No live events received yet.
          </div>
        ) : (
          items.map((item) => {
            const isExpanded = item.groupId ? Boolean(expandedGroups[item.groupId]) : false

            return (
              <div
                key={item.id}
                className="group relative flex gap-2.5 text-xs transition-opacity"
              >
                <div className="pt-0.5 shrink-0">
                  <Avatar id={item.actor} size="sm" showVendor />
                </div>

                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex flex-wrap items-baseline justify-between gap-1">
                    <span className="font-semibold text-foreground">{person(item.actor).name}</span>
                    <DualTime iso={item.ts} relative className="text-[11px]" />
                  </div>

                  {item.isGroup ? (
                    <div>
                      <button
                        type="button"
                        onClick={() => item.groupId && toggleGroup(item.groupId)}
                        className="inline-flex items-center gap-1.5 font-medium text-foreground hover:text-primary transition-colors text-left"
                      >
                        {isExpanded ? (
                          <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
                        )}
                        <span>{item.title}</span>
                      </button>

                      {isExpanded && (
                        <div className="mt-2 ml-2 pl-2 border-l border-border/80 space-y-2">
                          {item.events.map((sub) => (
                            <div key={sub.id} className="space-y-0.5">
                              <p className="text-foreground leading-relaxed">{sub.text}</p>
                              {sub.link && <ChatLink link={sub.link} className="text-[10px]" />}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-foreground leading-relaxed break-words">{item.title}</p>
                  )}

                  {item.link && !isExpanded && (
                    <div className="pt-0.5">
                      <ChatLink link={item.link} variant="open" />
                    </div>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </aside>
  )
}
