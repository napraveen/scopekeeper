import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DirectorMode } from '@/features/director/DirectorMode'
import { registerDemoController, useDemoStore } from '@/lib/demo'
import { useUiStore } from '@/stores/ui'

describe('DirectorMode Component', () => {
  const mockController = {
    play: vi.fn(),
    pause: vi.fn(),
    setSpeed: vi.fn(),
    step: vi.fn(),
    nextBeat: vi.fn(),
    prevBeat: vi.fn(),
    jumpToBeat: vi.fn(),
    flipNow: vi.fn(),
    morningNow: vi.fn(),
    reset: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    registerDemoController(mockController)
    useUiStore.setState({ directorOpen: true })
    useDemoStore.setState({ available: true, playing: false, speed: 60, cursor: 0, total: 20 })
  })

  it('renders director HUD when open and demo is available', () => {
    render(<DirectorMode />)

    expect(screen.getByRole('region', { name: /Director control panel/i })).toBeInTheDocument()
    expect(screen.getByText('Director Mode')).toBeInTheDocument()
    expect(screen.getByText('0 / 20')).toBeInTheDocument()
  })

  it('calls demo.play when Play is clicked', () => {
    render(<DirectorMode />)

    const playBtn = screen.getByRole('button', { name: /Play/i })
    fireEvent.click(playBtn)
    expect(mockController.play).toHaveBeenCalledTimes(1)
  })

  it('calls demo.step when Step is clicked', () => {
    render(<DirectorMode />)

    const stepBtn = screen.getByRole('button', { name: /Step/i })
    fireEvent.click(stepBtn)
    expect(mockController.step).toHaveBeenCalledTimes(1)
  })

  it('calls demo.reset when Reset is clicked', () => {
    render(<DirectorMode />)

    const resetBtn = screen.getByRole('button', { name: /Reset/i })
    fireEvent.click(resetBtn)
    expect(mockController.reset).toHaveBeenCalledTimes(1)
  })

  it('changes playback speed when speed button is clicked', () => {
    render(<DirectorMode />)

    const speedBtn = screen.getByRole('button', { name: '600×' })
    fireEvent.click(speedBtn)
    expect(mockController.setSpeed).toHaveBeenCalledWith(600)
  })

  it('handles keyboard shortcut D to toggle visibility', () => {
    render(<DirectorMode />)

    fireEvent.keyDown(window, { key: 'd' })
    expect(useUiStore.getState().directorOpen).toBe(false)
  })
})
