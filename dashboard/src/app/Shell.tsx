import { useState } from 'react'
import { Outlet } from 'react-router'
import { AskDrawer } from '@/features/asks/AskDrawer'
import { DirectorMode } from '@/features/director/DirectorMode'
import { CommandPalette } from '@/features/command-palette/CommandPalette'
import { Banners } from '@/components/Banners'
import { MobileNav } from '@/components/MobileNav'
import { Sidebar } from '@/components/Sidebar'
import { TopBar } from '@/components/TopBar'

export function Shell() {
  const [mobileSheetOpen, setMobileSheetOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-background font-sans text-foreground">
      {/* Collapsible Sidebar */}
      <Sidebar />

      {/* Main content column */}
      <div className="flex min-w-0 flex-1 flex-col pb-16 lg:pb-0">
        <Banners />
        <TopBar onOpenMobileNav={() => setMobileSheetOpen(true)} />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-[1440px] w-full mx-auto">
          <Outlet />
        </main>
      </div>

      {/* Mobile bottom navigation and more sheet */}
      <MobileNav sheetOpen={mobileSheetOpen} setSheetOpen={setMobileSheetOpen} />

      {/* Global slide-out Ask drawer */}
      <AskDrawer />

      {/* Director floating control panel */}
      <DirectorMode />

      {/* Global Command Palette (⌘K) */}
      <CommandPalette />
    </div>
  )
}
