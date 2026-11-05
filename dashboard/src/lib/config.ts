/**
 * Runtime configuration. Live mode works by setting `VITE_API_MODE=live` and
 * `VITE_API_BASE_URL`, with no code changes.
 */
export type ApiMode = 'mock' | 'live'

const rawMode = (import.meta.env.VITE_API_MODE as string | undefined)?.toLowerCase()

export const API_MODE: ApiMode = rawMode === 'live' ? 'live' : 'mock'

export const API_BASE_URL: string =
  API_MODE === 'live'
    ? ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000').replace(/\/$/, '')
    : ''

export const IS_MOCK = API_MODE === 'mock'

const TOKEN_KEY = 'scopekeeper.apiToken'

export function getApiToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setApiToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearApiToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}
