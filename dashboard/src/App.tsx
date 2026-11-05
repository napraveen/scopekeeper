import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from 'sonner'
import { Shell } from '@/app/Shell'
import { useLiveStream } from '@/app/useLiveStream'
import { useThemeSync } from '@/app/useTheme'
import { useWallClock } from '@/lib/clock'
import { MissionControlPage } from '@/pages/MissionControlPage'
import { AsksPage } from '@/pages/AsksPage'
import { ChangeRequestsPage } from '@/pages/ChangeRequestsPage'
import { PlanPage } from '@/pages/PlanPage'
import { ScopePage } from '@/pages/ScopePage'
import { RoomsPage } from '@/pages/RoomsPage'
import { LedgerPage } from '@/pages/LedgerPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { PublicChangeOrderPage } from '@/pages/PublicChangeOrderPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function AppShellWithHooks() {
  useWallClock()
  useThemeSync()
  useLiveStream()

  return (
    <Routes>
      {/* Public Change Order page (calm, printable, outside Shell navigation) */}
      <Route path="/co/:id" element={<PublicChangeOrderPage />} />

      {/* Main Back-Office Dashboard Shell */}
      <Route path="/" element={<Shell />}>
        <Route index element={<MissionControlPage />} />
        <Route path="asks" element={<AsksPage />} />
        <Route path="change-requests" element={<ChangeRequestsPage />} />
        <Route path="change-requests/:id" element={<ChangeRequestsPage />} />
        <Route path="plan" element={<PlanPage />} />
        <Route path="scope" element={<ScopePage />} />
        <Route path="rooms" element={<RoomsPage />} />
        <Route path="ledger" element={<LedgerPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={200}>
        <BrowserRouter>
          <AppShellWithHooks />
        </BrowserRouter>
        <Toaster position="bottom-right" richColors />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
