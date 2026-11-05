import { describe, expect, it } from 'vitest'
import { StoryEngine } from '../mocks/engine'
import { STORY } from '../mocks/story'

describe('story engine', () => {
  it('loads story steps in strict chronological order', () => {
    const engine = new StoryEngine(STORY, { publish: false })
    expect(engine.length).toBeGreaterThan(15)

    let prevTs = 0
    for (const step of STORY) {
      const ts = new Date(step.ts).getTime()
      expect(ts).toBeGreaterThanOrEqual(prevTs)
      prevTs = ts
    }
  })

  it('steps through beats and updates state', () => {
    const engine = new StoryEngine(STORY, { publish: false })
    expect(engine.position).toBe(0)

    // First step is the flip
    engine.step()
    expect(engine.position).toBe(1)
  })

  it('resets back to start', () => {
    const engine = new StoryEngine(STORY, { publish: false })
    engine.step()
    engine.step()
    expect(engine.position).toBe(2)

    engine.reset()
    expect(engine.position).toBe(0)
  })
})
