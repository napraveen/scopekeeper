import { useMemo, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
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

    return list.slice(0, 30)
  }, [events])

  if (isLoading) {
    return (
      <section aria-label="Live event activity feed" className="rounded-2xl border border-border/80 glass-card p-5">
        <Skeleton className="h-6 w-36 mb-4" />
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-xl" />
          ))}
        </div>
      </section>
    )
  }

  return (
    <section aria-label="Live event activity feed" className="rounded-2xl border border-border/80 glass-card p-5 sm:p-6 shadow-sm">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2">
            <span className="relative flex size-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
            </span>
            <h2 className="text-base font-bold tracking-tight text-foreground">Activity Stream</h2>
          </div>
          <span className="tabular rounded-full bg-secondary/80 border border-border/50 px-2 py-0.5 font-mono text-xs font-semibold text-muted-foreground">
            {events?.length ?? 0} events
          </span>
          <SwitchTag kind="Room link" label="Switch stream" />
        </div>
        <span className="text-xs font-medium text-muted-foreground">
          Live feed mirrored from Discord &amp; Slack rooms
        </span>
      </div>

      <div
        role="feed"
        aria-label="Activity stream"
        aria-live="polite"
        className="relative space-y-3.5 before:absolute before:bottom-3 before:top-3 before:left-4 before:w-px before:bg-border/70"
      >
        {items.map((item) => {
          if (item.isGroup && item.groupId) {
            const isExpanded = expandedGroups[item.groupId] ?? false
            return (
              <div
                key={item.id}
                className="relative flex flex-col gap-2 rounded-xl border border-border/70 bg-secondary/25 p-3.5 pl-11 transition-all hover:border-primary/40 hover:bg-secondary/40"
              >
                {/* Timeline connector dot */}
                <div className="absolute left-2.5 top-4 flex size-3.5 items-center justify-center rounded-full bg-card ring-2 ring-primary/40">
                  <div className="size-1.5 rounded-full bg-primary" />
                </div>

                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-2.5">
                    <Avatar id={item.actor} size="sm" showVendor />
                    <button
                      type="button"
                      onClick={() => toggleGroup(item.groupId!)}
                      className="flex items-center gap-1.5 text-xs font-bold text-foreground hover:text-primary transition-colors text-left"
                    >
                      {isExpanded ? (
                        <ChevronDown className="size-3.5 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="size-3.5 text-muted-foreground" />
                      )}
                      <span>{item.title}</span>
                    </button>
                  </div>

                  <div className="flex items-center gap-2 pl-6 sm:pl-0">
                    {item.link && <ChatLink link={item.link} variant="room" />}
                    <DualTime iso={item.ts} className="text-[11px]" />
                  </div>
                </div>

                {/* Sub-events inside the group */}
                {isExpanded && (
                  <div className="mt-2 space-y-2 border-t border-border/60 pt-2.5">
                    {item.events.map((sub) => (
                      <div
                        key={sub.id}
                        className="flex flex-col gap-1 rounded-lg bg-card/75 p-2 text-xs border border-border/40 sm:flex-row sm:items-center sm:justify-between"
                      >
                        <span className="text-foreground font-medium">{sub.text}</span>
                        <div className="flex items-center gap-2 shrink-0">
                          {sub.link && <ChatLink link={sub.link} variant="room" />}
                          <DualTime iso={sub.ts} className="text-[10px]" />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          }

          return (
            <div
              key={item.id}
              className="relative flex flex-col gap-2 rounded-xl border border-border/60 bg-card/60 p-3.5 pl-11 transition-all hover:border-primary/40 hover:bg-card"
            >
              {/* Timeline connector dot */}
              <div className="absolute left-2.5 top-4 flex size-3.5 items-center justify-center rounded-full bg-card ring-1 ring-border">
                <div className="size-1.5 rounded-full bg-muted-foreground/60" />
              </div>

              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2.5">
                  <Avatar id={item.actor} size="sm" showVendor />
                  <span className="text-xs font-semibold text-foreground">{item.title}</span>
                </div>

                <div className="flex items-center gap-2 pl-6 sm:pl-0">
                  {item.link && <ChatLink link={item.link} variant="room" />}
                  <DualTime iso={item.ts} className="text-[11px]" />
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
