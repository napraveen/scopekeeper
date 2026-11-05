import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { StreamStatus } from '@/lib/api/stream'

export type ThemePref = 'light' | 'dark' | 'desk'

interface UiState {
  themePref: ThemePref
  sidebarCollapsed: boolean
  switchLens: boolean
  directorOpen: boolean
  commandPaletteOpen: boolean
  activeAskId: string | null
  setThemePref(pref: ThemePref): void
  toggleSidebar(): void
  toggleSwitchLens(): void
  setDirectorOpen(open: boolean): void
  toggleDirector(): void
  setCommandPaletteOpen(open: boolean): void
  toggleCommandPalette(): void
  setActiveAskId(id: string | null): void
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      themePref: 'desk',
      sidebarCollapsed: false,
      switchLens: false,
      directorOpen:
        typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('director'),
      commandPaletteOpen: false,
      activeAskId: null,
      setThemePref: (themePref) => set({ themePref }),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      toggleSwitchLens: () => set((s) => ({ switchLens: !s.switchLens })),
      setDirectorOpen: (directorOpen) => set({ directorOpen }),
      toggleDirector: () => set((s) => ({ directorOpen: !s.directorOpen })),
      setCommandPaletteOpen: (commandPaletteOpen) => set({ commandPaletteOpen }),
      toggleCommandPalette: () => set((s) => ({ commandPaletteOpen: !s.commandPaletteOpen })),
      setActiveAskId: (activeAskId) => set({ activeAskId }),
    }),
    {
      name: 'scopekeeper.ui',
      partialize: (s) => ({ themePref: s.themePref, sidebarCollapsed: s.sidebarCollapsed }),
    },
  ),
)

interface ConnectionState {
  status: StreamStatus
  retry: number
  setStatus(status: StreamStatus): void
  reconnect(): void
}

export const useConnectionStore = create<ConnectionState>((set) => ({
  status: 'connecting',
  retry: 0,
  setStatus: (status) => set({ status }),
  reconnect: () => set((s) => ({ retry: s.retry + 1, status: 'connecting' })),
}))

interface PulseState {
  /** Bumped when an ask changes, so its card can glow briefly. */
  asks: Record<string, number>
  bump(askId: string): void
  clear(): void
}

export const usePulseStore = create<PulseState>((set) => ({
  asks: {},
  bump: (askId) => set((s) => ({ asks: { ...s.asks, [askId]: (s.asks[askId] ?? 0) + 1 } })),
  clear: () => set({ asks: {} }),
}))
