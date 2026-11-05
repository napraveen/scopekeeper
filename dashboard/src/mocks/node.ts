import { setupServer } from 'msw/node'
import { handlers } from './handlers'

/** The same handlers the app uses, for Vitest. */
export const server = setupServer(...handlers)
