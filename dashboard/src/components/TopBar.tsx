import {
  Laptop,
  Layers,
  Menu,
  Moon,
  Search,
  Sun,
} from 'lucide-react'
import { Avatar } from '@/components/Avatar'
import { LiveClocks } from '@/components/LiveClocks'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useDesk } from '@/lib/api/queries'
import { formatZoned } from '@/lib/format'
import { person } from '@/lib/people'
import { useConnectionStore, useUiStore } from '@/stores/ui'
import { cn } from '@/lib/utils'

export function TopBar({ onOpenMobileNav }: { onOpenMobileNav?: () => void }) {
  const { data: desk } = useDesk()
  const status = useConnectionStore((s) => s.status)
  const reconnect = useConnectionStore((s) => s.reconnect)
  const switchLens = useUiStore((s) => s.switchLens)
  const toggleSwitchLens = useUiStore((s) => s.toggleSwitchLens)
  const themePref = useUiStore((s) => s.themePref)
  const setThemePref = useUiStore((s) => s.setThemePref)

  const setCommandPaletteOpen = useUiStore((s) => s.setCommandPaletteOpen)

  const deskHolder = desk ? person(desk.holder) : null
  const deskUntil = desk ? formatZoned(desk.nextHandoverAt, 'agency') : ''

  return (
    <header className="sticky top-0 z-30 flex h-14 w-full items-center justify-between border-b border-border/80 bg-card/90 px-4 backdrop-blur-md">
      {/* Left side: mobile toggle + live dual clocks */}
      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          className="lg:hidden text-muted-foreground"
          onClick={onOpenMobileNav}
          aria-label="Toggle navigation menu"
        >
          <Menu className="size-4" />
        </Button>

        <div className="hidden sm:block">
          <LiveClocks />
        </div>
      </div>

      {/* Center: Desk pill */}
      {desk && (
        <div className="hidden md:flex items-center gap-2 rounded-full border border-border bg-secondary/50 px-3 py-1 text-xs">
          <span className="font-semibold text-foreground">Desk:</span>
          <span className="font-medium text-foreground">{deskHolder?.name}</span>
          <span className="text-muted-foreground">·</span>
          <span className="text-muted-foreground">
            {desk.mode} until {deskUntil}
          </span>
        </div>
      )}

      {/* Right side controls */}
      <div className="flex items-center gap-2">
        {/* Command palette search (⌘K) */}
        <Button
          type="button"
          variant="outline"
          size="xs"
          onClick={() => setCommandPaletteOpen(true)}
          className="gap-1.5 text-xs h-8 px-2.5 text-muted-foreground hover:text-foreground"
          title="Search commands, asks, and pages (⌘K)"
        >
          <Search className="size-3.5" />
          <span className="hidden md:inline">Search</span>
          <kbd className="hidden md:inline-flex rounded border border-border bg-secondary px-1 py-0.2 font-mono text-[9px] text-muted-foreground">
            ⌘K
          </kbd>
        </Button>

        {/* Switch lens toggle */}
        <Button
          type="button"
          variant={switchLens ? 'default' : 'outline'}
          size="xs"
          onClick={toggleSwitchLens}
          className={cn(
            'gap-1.5 font-medium transition-all text-xs h-8 px-2.5',
            switchLens && 'bg-primary text-primary-foreground shadow-xs',
          )}
          title="Toggle Switch lens (reveals agent rooms, roles, links, boundaries)"
        >
          <Layers className="size-3.5" />
          <span className="hidden sm:inline">Switch lens</span>
        </Button>

        {/* Connection status dot */}
        <button
          type="button"
          onClick={status === 'error' || status === 'closed' ? reconnect : undefined}
          title={`Connection status: ${status}. Click to reconnect if disconnected.`}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-secondary transition-colors"
        >
          <span
            className={cn(
              'size-2 rounded-full',
              status === 'open' && 'bg-emerald-500 shadow-xs',
              status === 'connecting' && 'bg-amber-500 animate-ping',
              (status === 'error' || status === 'closed') && 'bg-rose-500',
            )}
          />
          <span className="capitalize font-mono text-[11px] hidden lg:inline">
            {status === 'open' ? 'Live stream' : status}
          </span>
        </button>

        {/* Theme dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label="Select theme">
              {themePref === 'light' ? (
                <Sun className="size-4 text-amber-500" />
              ) : themePref === 'dark' ? (
                <Moon className="size-4 text-indigo-400" />
              ) : (
                <Laptop className="size-4 text-foreground" />
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setThemePref('desk')}>
              <Laptop className="size-4 mr-2" />
              <span>Follow the desk (default)</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setThemePref('light')}>
              <Sun className="size-4 mr-2 text-amber-500" />
              <span>Light theme</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setThemePref('dark')}>
              <Moon className="size-4 mr-2 text-indigo-400" />
              <span>Dark theme</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User avatar menu */}
        <div className="flex items-center gap-2 pl-1 border-l border-border/80">
          <Avatar id="priya" size="sm" />
          <div className="hidden xl:block text-left text-xs">
            <div className="font-semibold text-foreground leading-tight">Priya</div>
            <div className="text-[10px] text-muted-foreground">Account manager</div>
          </div>
        </div>
      </div>
    </header>
  )
}
