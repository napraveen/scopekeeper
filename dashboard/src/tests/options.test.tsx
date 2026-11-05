import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { OptionsCards } from '@/features/change-requests/OptionsCards'
import type { OptionQuote } from '@/lib/api/types'

const MOCK_OPTIONS: OptionQuote[] = [
  {
    key: 'A',
    label: 'Add it now',
    description: 'Full Android app now; moves M2 to Dec 24.',
    hours: 200,
    priceCents: 1035000,
    shiftDays: 12,
    newDue: '2026-12-24',
  },
  {
    key: 'D',
    label: 'Swap',
    description: 'View-only app in place of I9.',
    hours: 56,
    priceCents: 0,
    shiftDays: 0,
    swapIn: 'View-only Android app',
    swapOut: ['I9'],
  },
]

describe('OptionsCards', () => {
  it('renders all options with price and description', () => {
    render(<OptionsCards options={MOCK_OPTIONS} selectedKeys={['A', 'D']} />)

    expect(screen.getByText('Add it now')).toBeInTheDocument()
    expect(screen.getByText('$10,350')).toBeInTheDocument()
    expect(screen.getByText('+12 days (M2 due 2026-12-24)')).toBeInTheDocument()

    // Card D swap visualization
    expect(screen.getByText('Swap')).toBeInTheDocument()
    expect(screen.getByText('$0')).toBeInTheDocument()
    expect(screen.getByText(/Scope Swap/)).toBeInTheDocument()
  })

  it('marks chosen option with check badge', () => {
    render(<OptionsCards options={MOCK_OPTIONS} clientChoice="D" selectedKeys={['A', 'D']} />)

    expect(screen.getByText('Chosen')).toBeInTheDocument()
  })
})
