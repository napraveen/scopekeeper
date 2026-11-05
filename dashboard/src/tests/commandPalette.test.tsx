import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'
import { CommandPalette } from '@/features/command-palette/CommandPalette'
import { useDemoStore } from '@/lib/demo'
import { useUiStore } from '@/stores/ui'

function renderCommandPalette() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <CommandPalette />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('CommandPalette Component', () => {
  beforeEach(() => {
    useUiStore.setState({ commandPaletteOpen: true })
    useDemoStore.setState({ available: true })
  })

  it('renders command palette dialog when open', () => {
    renderCommandPalette()

    expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument()
    expect(screen.getByText('Mission Control')).toBeInTheDocument()
    expect(screen.getByText('Asks Registry')).toBeInTheDocument()
    expect(screen.getByText(/Toggle Switch Lens/i)).toBeInTheDocument()
  })

  it('shows demo story controls when demo mode is active', () => {
    renderCommandPalette()

    expect(screen.getByText(/Flip Client Desk Now/i)).toBeInTheDocument()
    expect(screen.getByText(/Morning Handover/i)).toBeInTheDocument()
  })

  it('toggles open state with Ctrl+K', () => {
    useUiStore.setState({ commandPaletteOpen: false })
    renderCommandPalette()

    fireEvent.keyDown(window, { key: 'k', ctrlKey: true })
    expect(useUiStore.getState().commandPaletteOpen).toBe(true)
  })
})
