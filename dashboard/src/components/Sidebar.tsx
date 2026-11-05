import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  FileCheck2,
  FileCode2,
  Inbox,
  LayoutDashboard,
  Network,
  Receipt,
  Settings,
  ToggleRight,
} from 'lucide-react'
import { Link, useLocation } from 'react-router'
import { useChangeRequests } from '@/lib/api/queries'
import { useUiStore } from '@/stores/ui'
import { cn } from '@/lib/utils'

export const NAV_ITEMS = [
  { to: '/', label: 'Mission Control', icon: LayoutDashboard },
  { to: '/asks', label: 'Asks', icon: Inbox },
  { to: '/change-requests', label: 'Change requests', icon: FileCheck2 },
  { to: '/plan', label: 'Plan', icon: Calendar },
  { to: '/scope', label: 'Scope', icon: FileCode2 },
  { to: '/rooms', label: 'Rooms', icon: Network },
  { to: '/ledger', label: 'Ledger', icon: Receipt },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  const location = useLocation()
  const collapsed = useUiStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useUiStore((s) => s.toggleSidebar)
  const { data: crs } = useChangeRequests()

  const pendingCrCount = (crs ?? []).filter(
    (c) => c.status === 'awaiting_approval' || c.status === 'awaiting_confirmation',
  ).length

  return (
    <aside
      className={cn(
        'relative hidden lg:flex flex-col border-r border-border/80 bg-sidebar transition-all duration-200 select-none z-20',
        collapsed ? 'w-16' : 'w-60',
      )}
    >
      {/* Brand logo & toggle */}
      <div className="flex h-14 items-center justify-between px-3.5 border-b border-border/80">
        <Link to="/" className="flex items-center gap-2 overflow-hidden">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-xs">
            <ToggleRight className="size-5" />
          </div>
          {!collapsed && (
            <div className="flex flex-col min-w-0">
              <span className="font-bold text-sm tracking-tight text-foreground leading-tight">
                ScopeKeeper
              </span>
              <span className="font-mono text-[10px] text-muted-foreground leading-none">
                Client Desk
              </span>
            </div>
          )}
        </Link>

        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="rounded-md p-1 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
        >
          {collapsed ? <ChevronRight className="size-4" /> : <ChevronLeft className="size-4" />}
        </button>
      </div>

      {/* Nav items */}
      <nav className="flex-1 space-y-1 p-2 overflow-y-auto scrollbar-thin">
        {NAV_ITEMS.map((item) => {
          const active = location.pathname === item.to
          const Icon = item.icon
          const showCrBadge = item.to === '/change-requests' && pendingCrCount > 0

          return (
            <Link
              key={item.to}
              to={item.to}
              title={collapsed ? item.label : undefined}
              className={cn(
                'group flex items-center gap-3 rounded-lg px-2.5 py-2 text-xs font-medium transition-colors',
                active
                  ? 'bg-accent text-accent-foreground font-semibold shadow-xs'
                  : 'text-muted-foreground hover:bg-secondary hover:text-foreground',
                collapsed && 'justify-center px-0',
              )}
            >
              <Icon className="size-4 shrink-0" />
              {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
              {!collapsed && showCrBadge && (
                <span className="tabular rounded-full bg-primary px-1.5 py-0.2 font-mono text-[10px] font-bold text-primary-foreground">
                  {pendingCrCount}
                </span>
              )}
              {collapsed && showCrBadge && (
                <span className="absolute top-1.5 right-1.5 size-2 rounded-full bg-primary" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer: Built on Switch text */}
      <div className="p-3 border-t border-border/70 text-center">
        {!collapsed ? (
          <p className="text-[11px] text-muted-foreground">
            Built on <span className="font-semibold text-foreground">Switch</span>
          </p>
        ) : (
          <span title="Built on Switch" className="text-[10px] font-mono text-muted-foreground">
            Switch
          </span>
        )}
      </div>
    </aside>
  )
}
