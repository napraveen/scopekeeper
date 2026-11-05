/** Applies the theme: Light, Dark, or Follow the desk (dark while Scout holds it). */
import { useEffect, useRef } from 'react'
import { useDesk } from '@/lib/api/queries'
import { useUiStore } from '@/stores/ui'

export function useEffectiveTheme(): 'light' | 'dark' {
  const pref = useUiStore((s) => s.themePref)
  const { data: desk } = useDesk()
  if (pref === 'desk') return desk?.holder === 'scout' ? 'dark' : 'light'
  return pref
}

export function useThemeSync(): void {
  const theme = useEffectiveTheme()
  const first = useRef(true)
  useEffect(() => {
    const root = document.documentElement
    const isDark = root.classList.contains('dark')
    if ((theme === 'dark') === isDark) {
      first.current = false
      return
    }
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!first.current && !reduce) root.classList.add('theme-transition')
    root.classList.toggle('dark', theme === 'dark')
    first.current = false
    const id = window.setTimeout(() => root.classList.remove('theme-transition'), 450)
    return () => window.clearTimeout(id)
  }, [theme])
}
