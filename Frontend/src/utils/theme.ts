import { incrementThemeVersion } from '@/stores/themeStore'

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
  if (effective === 'dark') {
    // Inject style tag that comes after Element Plus CSS → wins cascade order
    const style = getOrCreateDarkStyle()
    style.textContent = `
      html.theme-dark .el-card,
      html.theme-dark .el-card[class*="is-"] {
        --el-card-bg-color: #141720 !important;
        --el-card-border-color: rgba(255,255,255,0.1) !important;
        background: #141720 !important;
        border-color: rgba(255,255,255,0.1) !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.45) !important;
      }
      html.theme-dark .el-card__header { background: #141720 !important; border-color: rgba(255,255,255,0.1) !important; }
      html.theme-dark .el-card__body { background: #141720 !important; }
      html.theme-dark .stat-icon { color: #f0f2f8 !important; background: #141720 !important; }
      html.theme-dark .stat-icon .el-icon svg { fill: #f0f2f8 !important; }
      html.theme-dark .quick-icon .el-icon svg { fill: #c8cdd8 !important; }
      html.theme-dark .el-table { background: #0d0f14 !important; }
      html.theme-dark .el-table__header th { background: #1c2030 !important; color: #f0f2f8 !important; }
      html.theme-dark .el-table__row td { background: #141720 !important; color: #c8cdd8 !important; }
      html.theme-dark .el-table__body tr:hover > td { background: #1c2030 !important; }
      html.theme-dark .el-input__wrapper,
      html.theme-dark .el-textarea__inner { background: #141720 !important; color: #f0f2f8 !important; border-color: rgba(255,255,255,0.1) !important; }
      html.theme-dark .el-input__inner { color: #f0f2f8 !important; }
      html.theme-dark .el-input__wrapper .el-input__prefix .el-input__prefix-inner,
      html.theme-dark .el-input__wrapper .el-input__suffix .el-input__suffix-inner { color: #8b93a8 !important; }
      html.theme-dark .el-dropdown-menu { background: #141720 !important; border-color: rgba(255,255,255,0.1) !important; }
      html.theme-dark .el-dropdown-menu__item { color: #c8cdd8 !important; }
      html.theme-dark .el-dropdown-menu__item:hover { background: rgba(255,255,255,0.07) !important; color: #f0f2f8 !important; }
      html.theme-dark .el-select-dropdown { background: #141720 !important; border-color: rgba(255,255,255,0.1) !important; }
      html.theme-dark .el-select-dropdown__item { color: #c8cdd8 !important; }
      html.theme-dark .el-select-dropdown__item:hover { background: rgba(255,255,255,0.07) !important; color: #f0f2f8 !important; }
      html.theme-dark .el-scrollbar__thumb { background: rgba(255,255,255,0.2) !important; }
      html.theme-dark .nav-actions .el-button { background: #141720 !important; border-color: rgba(255,255,255,0.1) !important; color: #c8cdd8 !important; box-shadow: none !important; }
      html.theme-dark .nav-actions .el-button:hover { background: rgba(255,255,255,0.07) !important; color: #f0f2f8 !important; }
      html.theme-dark .nav-actions .el-button--primary { background: #f0f2f8 !important; border-color: #f0f2f8 !important; color: #0d0f14 !important; font-weight: 600 !important; box-shadow: none !important; }
      html.theme-dark .nav-actions .el-button--primary:hover { background: #c8cdd8 !important; }
      html.theme-dark .el-button--primary { background: #f0f2f8 !important; border-color: #f0f2f8 !important; color: #0d0f14 !important; font-weight: 600 !important; box-shadow: none !important; }
      html.theme-dark .el-button--primary:hover { background: #c8cdd8 !important; }
      html.theme-dark .el-button:not(.el-button--primary) { background: #141720 !important; border-color: rgba(255,255,255,0.1) !important; color: #c8cdd8 !important; box-shadow: none !important; }
      html.theme-dark .el-button:not(.el-button--primary):hover { background: rgba(255,255,255,0.07) !important; color: #f0f2f8 !important; }
      html.theme-dark .el-button:not(.el-button--primary) .el-icon { color: #8b93a8 !important; }
      html.theme-dark .el-button:not(.el-button--primary) .el-icon svg { fill: #8b93a8 !important; }
      html.theme-dark .el-button:not(.el-button--primary):hover .el-icon { color: #f0f2f8 !important; }
      html.theme-dark .el-button:not(.el-button--primary):hover .el-icon svg { fill: #f0f2f8 !important; }
    `  } else {
    clearDarkStyle()
  }
}

export function readCurrentTheme(): ThemeMode {
  return readSavedTheme()
}

export function toggleTheme() {
  const current = readSavedTheme()
  const next: ThemeMode = current === 'dark' ? 'light' : 'dark'
  applyTheme(next)
  incrementThemeVersion()
  try {
    const raw = localStorage.getItem(THEME_KEY)
    const prefs = JSON.parse(raw ?? '{}')
    prefs.theme = next
    localStorage.setItem(THEME_KEY, JSON.stringify(prefs))
  } catch { /* ignore */ }
}

let _mediaListenerAttached = false

// Inject a <style> tag at the end of <head> that overrides Element Plus dark theme !important CSS vars.
// This tag's cascade origin is "author embedded sheets" which comes AFTER external stylesheets,
// so its !important declarations can override Element Plus's !important.
function getOrCreateDarkStyle(): HTMLStyleElement {
  let el = document.getElementById('flowly-dark-override') as HTMLStyleElement | null
  if (!el) {
    el = document.createElement('style')
    el.id = 'flowly-dark-override'
    el.dataset.flavor = 'dark'
    document.head.appendChild(el)
  }
  return el
}

function clearDarkStyle() {
  const el = document.getElementById('flowly-dark-override')
  if (el) el.textContent = ''
}

export function applyTheme(mode?: ThemeMode) {
  const m = mode ?? readSavedTheme()
  if (m === 'auto') {
    applyThemeClass(systemPrefersDark() ? 'dark' : 'light')
    incrementThemeVersion()
    if (!_mediaListenerAttached) {
      _mediaListenerAttached = true
      const mq = window.matchMedia?.('(prefers-color-scheme: dark)')
      mq?.addEventListener?.('change', () => {
        const now = readSavedTheme()
        if (now === 'auto') {
          applyThemeClass(systemPrefersDark() ? 'dark' : 'light')
          incrementThemeVersion()
        }
      })
    }
    return
  }
  applyThemeClass(m)
  incrementThemeVersion()
}

