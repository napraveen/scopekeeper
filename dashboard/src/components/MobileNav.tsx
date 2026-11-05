import {
  Calendar,
  FileCheck2,
  FileCode2,
  Inbox,
  LayoutDashboard,
  MoreHorizontal,
  Network,
  Receipt,
  Settings,
  ToggleRight,
} from 'lucide-react'
import { Link, useLocation } from 'react-router'
import { LiveClocks } from '@/components/LiveClocks'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { useChangeRequests } from '@/lib/api/queries'
import { cn } from '@/lib/utils'

export function MobileNav({
  sheetOpen,
  setSheetOpen,
}: {
  sheetOpen: boolean
  setSheetOpen: (open: boolean) => void
}) {
  const location = useLocation()
  const { data: crs } = useChangeRequests()

  const pendingCrCount = (crs ?? []).filter(
    (c) => c.status === 'awaiting_approval' || c.status === 'awaiting_confirmation',
  ).length

  const bottomTabs = [
    { to: '/', label: 'Mission', icon: LayoutDashboard },
    { to: '/asks', label: 'Asks', icon: Inbox },
    { to: '/change-requests', label: 'Changes', icon: FileCheck2, badge: pendingCrCount },
    { to: '/plan', label: 'Plan', icon: Calendar },
  ]

  const moreTabs = [
    { to: '/scope', label: 'Scope (Contract Map)', icon: FileCode2 },
    { to: '/rooms', label: 'Rooms (Switch Map)', icon: Network },
    { to: '/ledger', label: 'Ledger & Billing', icon: Receipt },
    { to: '/settings', label: 'Settings & Rates', icon: Settings },
  ]

  return (
    <>
      {/* Bottom bar for screens < lg */}
      <nav
        aria-label="Mobile navigation"
        className="fixed bottom-0 left-0 right-0 z-40 flex h-14 items-center justify-around border-t border-border/80 bg-card/95 backdrop-blur-md lg:hidden"
      >
        {bottomTabs.map((tab) => {
          const active = location.pathname === tab.to
          const Icon = tab.icon

          return (
            <Link
              key={tab.to}
              to={tab.to}
              className={cn(
                'relative flex flex-col items-center justify-center gap-0.5 py-1 text-[11px] font-medium transition-colors',
                active ? 'text-primary font-semibold' : 'text-muted-foreground',
              )}
            >
              <div className="relative">
                <Icon className="size-4" />
                {Boolean(tab.badge && tab.badge > 0) && (
                  <span className="absolute -top-1 -right-2 size-2 rounded-full bg-primary" />
                )}
              </div>
              <span>{tab.label}</span>
            </Link>
          )
        })}

        <button
          type="button"
          onClick={() => setSheetOpen(true)}
          className="flex flex-col items-center justify-center gap-0.5 py-1 text-[11px] font-medium text-muted-foreground hover:text-foreground"
        >
          <MoreHorizontal className="size-4" />
          <span>More</span>
        </button>
      </nav>

      {/* More sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="bottom" className="rounded-t-2xl p-5 border-t border-border">
          <SheetHeader className="pb-3 border-b border-border/70 text-left">
            <div className="flex items-center gap-2">
              <ToggleRight className="size-5 text-primary" />
              <SheetTitle className="text-base font-bold text-foreground">ScopeKeeper</SheetTitle>
            </div>
            <SheetDescription className="text-xs">
              Navigation &amp; Global Clocks
            </SheetDescription>
          </SheetHeader>

          <div className="py-4">
            <div className="mb-4 rounded-xl border border-border bg-secondary/30 p-3">
              <div className="text-[11px] font-medium text-muted-foreground uppercase mb-2">
                Team Clocks
              </div>
              <LiveClocks />
            </div>

            <div className="space-y-1">
              {moreTabs.map((item) => {
                const Icon = item.icon
                const active = location.pathname === item.to

                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    onClick={() => setSheetOpen(false)}
                    className={cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2.5 text-xs font-medium transition-colors',
                      active
                        ? 'bg-accent text-accent-foreground font-semibold'
                        : 'text-muted-foreground hover:bg-secondary hover:text-foreground',
                    )}
                  >
                    <Icon className="size-4 text-primary" />
                    <span>{item.label}</span>
                  </Link>
                )
              })}
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
