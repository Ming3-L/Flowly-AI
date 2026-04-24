export type ThemeMode = 'light' | 'dark' | 'auto'

const THEME_KEY = 'flowly_preferences'

function readSavedTheme(): ThemeMode {
  try {
    const raw = localStorage.getItem(THEME_KEY)
    if (!raw) return 'light'
    const prefs = JSON.parse(raw)
    const t = String(prefs?.theme ?? 'light')
    if (t === 'dark' || t === 'light' || t === 'auto') return t
    return 'light'
  } catch {
    return 'light'
  }
}

function systemPrefersDark(): boolean {
  return window.matchMedia?.('(prefers-color-scheme: dark)')?.matches ?? false
}

function applyThemeClass(effective: 'light' | 'dark') {
  const el = document.documentElement
  el.classList.toggle('theme-dark', effective === 'dark')
  el.classList.toggle('theme-light', effective === 'light')
  el.style.colorScheme = effective
}

let _mediaListenerAttached = false

export function applyTheme(mode?: ThemeMode) {
  const m = mode ?? readSavedTheme()
  if (m === 'auto') {
    applyThemeClass(systemPrefersDark() ? 'dark' : 'light')
    if (!_mediaListenerAttached) {
      _mediaListenerAttached = true
      const mq = window.matchMedia?.('(prefers-color-scheme: dark)')
      mq?.addEventListener?.('change', () => {
        const now = readSavedTheme()
        if (now === 'auto') applyThemeClass(systemPrefersDark() ? 'dark' : 'light')
      })
    }
    return
  }
  applyThemeClass(m)
}

