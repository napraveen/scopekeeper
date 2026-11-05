import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SwitchTag } from '@/components/SwitchTag'
import { TooltipProvider } from '@/components/ui/tooltip'
import { useUiStore } from '@/stores/ui'

describe('Switch Lens & SwitchTag', () => {
  it('does not render SwitchTag when switchLens is off', () => {
    useUiStore.setState({ switchLens: false })

    render(
      <TooltipProvider>
        <SwitchTag kind="Role" label="Role · @client-desk" />
      </TooltipProvider>,
    )

    expect(screen.queryByText('Role · @client-desk')).toBeNull()
  })

  it('renders SwitchTag when switchLens is toggled on', () => {
    useUiStore.setState({ switchLens: true })

    render(
      <TooltipProvider>
        <SwitchTag kind="Role" label="Role · @client-desk" />
      </TooltipProvider>,
    )

    expect(screen.getByText('Role · @client-desk')).toBeInTheDocument()
  })
})
