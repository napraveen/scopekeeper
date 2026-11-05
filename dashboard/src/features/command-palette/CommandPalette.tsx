import { useEffect } from 'react'
import { Command } from 'cmdk'
import {
  ArrowRightLeft,
  Calendar,
  FileCheck2,
  FileCode2,
  Inbox,
  Laptop,
  Layers,
  LayoutDashboard,
  Network,
  Receipt,
  RotateCcw,
  Search,
  Settings,
  SkipForward,
  Sun,
  Zap,
} from 'lucide-react'
import { useNavigate } from 'react-router'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { demo, useDemoStore } from '@/lib/demo'
import { useAsks, useChangeRequests, useScope } from '@/lib/api/queries'
import { useUiStore } from '@/stores/ui'
import { toast } from 'sonner'

export function CommandPalette() {
  const navigate = useNavigate()
  const open = useUiStore((s) => s.commandPaletteOpen)
  const setOpen = useUiStore((s) => s.setCommandPaletteOpen)
  const toggleOpen = useUiStore((s) => s.toggleCommandPalette)

  const toggleSwitchLens = useUiStore((s) => s.toggleSwitchLens)
  const switchLens = useUiStore((s) => s.switchLens)
  const setThemePref = useUiStore((s) => s.setThemePref)
  const toggleDirector = useUiStore((s) => s.toggleDirector)
  const setActiveAskId = useUiStore((s) => s.setActiveAskId)

  const demoAvailable = useDemoStore((s) => s.available)

  const { data: asksData } = useAsks()
  const { data: crsData } = useChangeRequests()
  const { data: scopeData } = useScope()

  const asks = asksData?.items ?? []
  const crs = crsData ?? []
  const clauses = scopeData?.clauses ?? []

  // Global hotkey: Meta+K or Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault()
        toggleOpen()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [toggleOpen])

  const runCommand = (action: () => void) => {
    setOpen(false)
    action()
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="p-0 overflow-hidden sm:max-w-xl border-border bg-card shadow-2xl">
        <Command className="flex h-full w-full flex-col overflow-hidden rounded-xl bg-card text-foreground">
          <div className="flex items-center border-b border-border/80 px-3 py-2">
            <Search className="size-4 shrink-0 text-muted-foreground mr-2" />
            <Command.Input
              placeholder="Type a command, ask ID, change request, or page..."
              className="flex h-10 w-full rounded-md bg-transparent text-xs text-foreground placeholder:text-muted-foreground outline-hidden focus:outline-hidden"
            />
            <kbd className="hidden sm:inline-block rounded border border-border bg-secondary px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
              ESC
            </kbd>
          </div>

          <Command.List className="max-h-80 overflow-y-auto p-2 scrollbar-thin">
            <Command.Empty className="py-6 text-center text-xs text-muted-foreground">
              No results found.
            </Command.Empty>

            {/* Navigation Pages */}
            <Command.Group heading="Navigation" className="px-2 py-1 text-[11px] font-semibold text-muted-foreground">
              <Command.Item
                onSelect={() => runCommand(() => navigate('/'))}
                className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
              >
                <LayoutDashboard className="size-4 text-primary" />
                <span>Mission Control</span>
              </Command.Item>
              <Command.Item
                onSelect={() => runCommand(() => navigate('/asks'))}
                className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
              >
                <Inbox className="size-4 text-primary" />
                <span>Asks Registry</span>
              </Command.Item>
              <Command.Item
                onSelect={() => runCommand(() => navigate('/change-requests'))}
                className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
              >
                <FileCheck2 className="size-4 text-primary" />
                <span>Change Requests</span>
              </Command.Item>
              <Command.Item
                onSelect={() => runCommand(() => navigate('/plan'))}
                className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
              >
                <Calendar className="size-4 text-primary" />
                <span>Delivery Plan</span>
              </Command.Item>
              <Command.Item
                onSelect={() => runCommand(() => navigate('/scope'))}
                className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
              >
                <FileCode2 className="size-4 text-primary" />
                <span>Scope (Contract Map)</span>
              </Command.Item>
              <Command.Item
                onSelect={() => runCommand(() => navigate('/rooms'))}
                className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
              >
                <Network className="size-4 text-primary" />
                <span>Rooms (Switch Map)</span>
              </Command.Item>
              <Command.Item
                onSelect={() => runCommand(() => navigate('/ledger'))}
                className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
              >
                <Receipt className="size-4 text-primary" />
                <span>Scope Ledger &amp; Billing</span>
              </Command.Item>
              <Command.Item
                onSelect={() => runCommand(() => navigate('/settings'))}
                className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
              >
                <Settings className="size-4 text-primary" />
                <span>Settings &amp; Rate Governance</span>
              </Command.Item>
            </Command.Group>

            {/* Quick Actions */}
            <Command.Group heading="Actions" className="mt-2 px-2 py-1 text-[11px] font-semibold text-muted-foreground">
              <Command.Item
                onSelect={() =>
                  runCommand(() => {
                    toggleSwitchLens()
                    toast.info(`Switch lens ${!switchLens ? 'enabled' : 'disabled'}`)
                  })
                }
                className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
              >
                <Layers className="size-4 text-primary" />
                <span>Toggle Switch Lens ({switchLens ? 'Currently ON' : 'Currently OFF'})</span>
              </Command.Item>
              <Command.Item
                onSelect={() =>
                  runCommand(() => {
                    toggleDirector()
                  })
                }
                className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
              >
                <Zap className="size-4 text-amber-500" />
                <span>Toggle Director Mode HUD (Hotkey: D)</span>
              </Command.Item>
              <Command.Item
                onSelect={() => runCommand(() => setThemePref('desk'))}
                className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
              >
                <Laptop className="size-4 text-muted-foreground" />
                <span>Set Theme: Follow the desk (Priya: day, Scout: night)</span>
              </Command.Item>
            </Command.Group>

            {/* Demo Actions */}
            {demoAvailable && (
              <Command.Group heading="Demo Story Controls" className="mt-2 px-2 py-1 text-[11px] font-semibold text-muted-foreground">
                <Command.Item
                  onSelect={() =>
                    runCommand(() => {
                      demo().flipNow()
                      toast.success('Triggered desk flip handover')
                    })
                  }
                  className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
                >
                  <ArrowRightLeft className="size-4 text-primary" />
                  <span>Flip Client Desk Now (Handover)</span>
                </Command.Item>
                <Command.Item
                  onSelect={() =>
                    runCommand(() => {
                      demo().morningNow()
                      toast.success('Triggered 09:30 AM morning brief')
                    })
                  }
                  className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
                >
                  <Sun className="size-4 text-amber-500" />
                  <span>Morning Handover &amp; Brief Now</span>
                </Command.Item>
                <Command.Item
                  onSelect={() =>
                    runCommand(() => {
                      demo().nextBeat()
                    })
                  }
                  className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
                >
                  <SkipForward className="size-4 text-muted-foreground" />
                  <span>Jump to Next Story Beat (Hotkey: ])</span>
                </Command.Item>
                <Command.Item
                  onSelect={() =>
                    runCommand(() => {
                      demo().reset()
                      toast.info('Story reset to seed state')
                    })
                  }
                  className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
                >
                  <RotateCcw className="size-4 text-muted-foreground" />
                  <span>Reset Demo Story (Hotkey: R)</span>
                </Command.Item>
              </Command.Group>
            )}

            {/* Change Requests */}
            {crs.length > 0 && (
              <Command.Group heading="Change Requests" className="mt-2 px-2 py-1 text-[11px] font-semibold text-muted-foreground">
                {crs.map((cr) => (
                  <Command.Item
                    key={cr.id}
                    onSelect={() => runCommand(() => navigate(`/change-requests/${cr.id}`))}
                    className="flex cursor-pointer items-center justify-between rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-primary">{cr.id}</span>
                      <span className="font-medium">{cr.title}</span>
                    </div>
                    <span className="rounded bg-secondary px-1.5 py-0.2 font-mono text-[10px] uppercase text-muted-foreground">
                      {cr.status.replace('_', ' ')}
                    </span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {/* Asks */}
            {asks.length > 0 && (
              <Command.Group heading="Client Asks" className="mt-2 px-2 py-1 text-[11px] font-semibold text-muted-foreground">
                {asks.map((ask) => (
                  <Command.Item
                    key={ask.id}
                    onSelect={() =>
                      runCommand(() => {
                        setActiveAskId(ask.id)
                      })
                    }
                    className="flex cursor-pointer items-center justify-between rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
                  >
                    <div className="flex items-center gap-2 truncate max-w-sm">
                      <span className="font-mono font-bold text-foreground">{ask.id}</span>
                      <span className="truncate text-muted-foreground">“{ask.quote}”</span>
                    </div>
                    <span className="font-mono text-[10px] text-primary">{ask.category}</span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {/* Scope Clauses */}
            {clauses.length > 0 && (
              <Command.Group heading="SOW Clauses" className="mt-2 px-2 py-1 text-[11px] font-semibold text-muted-foreground">
                {clauses.map((clause) => (
                  <Command.Item
                    key={clause.id}
                    onSelect={() => runCommand(() => navigate('/scope'))}
                    className="flex cursor-pointer items-center justify-between rounded-lg px-2.5 py-2 text-xs text-foreground hover:bg-secondary aria-selected:bg-secondary transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-muted-foreground">§{clause.id}</span>
                      <span className="font-medium">{clause.title}</span>
                    </div>
                    <span className="font-mono text-[10px] text-muted-foreground">
                      {clause.kind === 'in' ? 'In scope' : 'Exclusion'}
                    </span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  )
}
