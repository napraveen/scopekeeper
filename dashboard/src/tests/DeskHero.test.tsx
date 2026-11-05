import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'
import { DeskHero } from '@/features/desk/DeskHero'
import { TooltipProvider } from '@/components/ui/tooltip'

function renderDeskHero() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <DeskHero />
      </TooltipProvider>
    </QueryClientProvider>,
  )
}

describe('DeskHero component', () => {
  it('renders desk hero switch with initial Priya state', async () => {
    renderDeskHero()

    // Priya should appear
    expect(await screen.findAllByText(/Priya/)).not.toHaveLength(0)
    // Scout should appear
    expect(screen.getAllByText(/Scout/)).not.toHaveLength(0)
    // Role pill should be present
    expect(screen.getByText('@client-desk')).toBeInTheDocument()
  })
})
