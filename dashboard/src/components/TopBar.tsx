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
  const isScout = desk?.holder === 'scout'

  return (
    <header className="sticky top-0 z-30 flex h-14 w-full items-center justify-between border-b border-border/80 bg-card/85 px-4 backdrop-blur-md shadow-2xs">
      {/* Left side: mobile toggle + live dual clocks */}
      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          className="lg:hidden text-muted-foreground hover:text-foreground"
          onClick={onOpenMobileNav}
          aria-label="Toggle navigation menu"
        >
          <Menu className="size-4" />
        </Button>

        <div className="hidden sm:block">
          <LiveClocks />
        </div>
      </div>

      {/* Center: Desk pill with live beacon */}
      {desk && (
        <div className={cn(
          'hidden md:flex items-center gap-2 rounded-full border px-3 py-1 text-xs transition-all shadow-2xs',
          isScout
            ? 'border-indigo-500/30 bg-indigo-500/10 text-indigo-700 dark:text-indigo-200'
            : 'border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-200',
        )}>
          <span className="relative flex size-2">
            <span className={cn('absolute inline-flex h-full w-full animate-ping rounded-full opacity-75', isScout ? 'bg-indigo-400' : 'bg-amber-400')} />
            <span className={cn('relative inline-flex size-2 rounded-full', isScout ? 'bg-indigo-500' : 'bg-amber-500')} />
          </span>
          <span className="font-semibold text-foreground">Desk:</span>
          <span className="font-bold text-foreground">{deskHolder?.name}</span>
          <span className="text-muted-foreground/60">·</span>
          <span className="font-medium">
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
          className="gap-1.5 text-xs h-8 px-2.5 text-muted-foreground hover:text-foreground border-border/80 hover:border-border transition-colors"
          title="Search commands, asks, and pages (⌘K)"
        >
          <Search className="size-3.5" />
          <span className="hidden md:inline font-medium">Search</span>
          <kbd className="hidden md:inline-flex rounded border border-border/80 bg-secondary/80 px-1 py-0.2 font-mono text-[9px] text-muted-foreground">
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
            'gap-1.5 font-semibold transition-all text-xs h-8 px-2.5',
            switchLens && 'bg-primary text-primary-foreground shadow-sm ring-1 ring-primary/40',
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
          className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-muted-foreground hover:bg-secondary transition-colors"
        >
          <span
            className={cn(
              'size-2 rounded-full',
              status === 'open' && 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.7)]',
              status === 'connecting' && 'bg-amber-500 animate-ping',
              (status === 'error' || status === 'closed') && 'bg-rose-500',
            )}
          />
          <span className="capitalize font-mono text-[11px] hidden lg:inline font-medium">
            {status === 'open' ? 'Live stream' : status}
          </span>
        </button>

        {/* Theme dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label="Select theme" className="hover:bg-secondary">
              {themePref === 'light' ? (
                <Sun className="size-4 text-amber-500" />
              ) : themePref === 'dark' ? (
                <Moon className="size-4 text-indigo-400" />
              ) : (
                <Laptop className="size-4 text-foreground" />
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52">
            <DropdownMenuItem onClick={() => setThemePref('desk')} className="cursor-pointer">
              <Laptop className="size-4 mr-2" />
              <div className="flex flex-col">
                <span className="font-semibold text-xs">Follow the desk</span>
                <span className="text-[10px] text-muted-foreground">Priya: day, Scout: night</span>
              </div>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setThemePref('light')} className="cursor-pointer">
              <Sun className="size-4 mr-2 text-amber-500" />
              <span className="text-xs">Light theme</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setThemePref('dark')} className="cursor-pointer">
              <Moon className="size-4 mr-2 text-indigo-400" />
              <span className="text-xs">Dark theme</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User avatar menu */}
        <div className="flex items-center gap-2 pl-2 border-l border-border/80">
          <Avatar id="priya" size="sm" />
          <div className="hidden xl:block text-left text-xs">
            <div className="font-bold text-foreground leading-tight">Priya</div>
            <div className="text-[10px] text-muted-foreground font-medium">Account manager</div>
          </div>
        </div>
      </div>
    </header>
  )
}
