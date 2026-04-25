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
      html.theme-dark body { background: #000000 !important; }
      html.theme-dark .el-card,
      html.theme-dark .el-card[class*="is-"] {
        --el-card-bg-color: #0a0a0a !important;
        --el-card-border-color: rgba(255,255,255,0.12) !important;
        background: #0a0a0a !important;
        border-color: rgba(255,255,255,0.12) !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.8) !important;
      }
      html.theme-dark .el-card__header { background: #0a0a0a !important; border-color: rgba(255,255,255,0.12) !important; }
      html.theme-dark .el-card__body { background: #0a0a0a !important; }
      html.theme-dark .el-table { background: #000000 !important; }
      html.theme-dark .el-table__header th { background: #141414 !important; color: #ffffff !important; }
      html.theme-dark .el-table__row td { background: #0a0a0a !important; color: #e0e0e0 !important; }
      html.theme-dark .el-table__body tr:hover > td { background: #141414 !important; }
      html.theme-dark .el-input__wrapper,
      html.theme-dark .el-textarea__inner { background: #0a0a0a !important; color: #ffffff !important; border-color: rgba(255,255,255,0.12) !important; }
      html.theme-dark .el-input__inner { color: #ffffff !important; }
      html.theme-dark .el-input__wrapper .el-input__prefix .el-input__prefix-inner,
      html.theme-dark .el-input__wrapper .el-input__suffix .el-input__suffix-inner { color: #888888 !important; }
      html.theme-dark .el-dropdown-menu { background: #0a0a0a !important; border-color: rgba(255,255,255,0.12) !important; }
      html.theme-dark .el-dropdown-menu__item { color: #e0e0e0 !important; }
      html.theme-dark .el-dropdown-menu__item:hover { background: rgba(255,255,255,0.08) !important; color: #ffffff !important; }
      html.theme-dark .el-select-dropdown { background: #0a0a0a !important; border-color: rgba(255,255,255,0.12) !important; }
      html.theme-dark .el-select-dropdown__item { color: #e0e0e0 !important; }
      html.theme-dark .el-select-dropdown__item:hover { background: rgba(255,255,255,0.08) !important; color: #ffffff !important; }
      html.theme-dark .el-scrollbar__thumb { background: rgba(255,255,255,0.2) !important; }
      html.theme-dark .el-button--primary { background: #ffffff !important; border-color: #ffffff !important; color: #000000 !important; font-weight: 600 !important; box-shadow: none !important; }
      html.theme-dark .el-button--primary:hover { background: #e0e0e0 !important; }
      html.theme-dark .el-button:not(.el-button--primary) { background: #0a0a0a !important; border-color: rgba(255,255,255,0.12) !important; color: #e0e0e0 !important; box-shadow: none !important; }
      html.theme-dark .el-button:not(.el-button--primary):hover { background: rgba(255,255,255,0.08) !important; color: #ffffff !important; }
      html.theme-dark nav.el-menu .el-menu-item.is-active { background: #ffffff !important; color: #000000 !important; border-bottom-color: #000000 !important; }
      html.theme-dark nav.el-menu .el-menu-item:not(.is-active):hover { background: rgba(255,255,255,0.1) !important; color: #ffffff !important; }
      html.theme-dark nav.el-menu .el-menu-item { color: rgba(255,255,255,0.7) !important; }
      html.theme-dark .app-nav { background: #000000 !important; }
      html.theme-dark .home-page { background: #000000 !important; }
      html.theme-dark .home-nav { background: #000000 !important; }
      html.theme-dark .hero { background: #000000 !important; }
      html.theme-dark .demo-section { background: #000000 !important; }
      html.theme-dark .features-section { background: #000000 !important; }
      html.theme-dark .pricing-section { background: #000000 !important; }
      html.theme-dark .testimonials-section { background: #000000 !important; }
      html.theme-dark .demo-header { background: #0a0a0a !important; }
      html.theme-dark .demo-toolbar { background: #0a0a0a !important; }
      html.theme-dark .demo-content { background: #0a0a0a !important; }
      html.theme-dark .demo-palette { background: #141414 !important; }
      html.theme-dark .demo-canvas { background-color: #000000 !important; background-image: radial-gradient(rgba(255,255,255,0.1) 1px, transparent 1px) !important; }
      html.theme-dark .feature-card { background: #0a0a0a !important; }
      html.theme-dark .pricing-card { background: #0a0a0a !important; }
      html.theme-dark .testimonial-card { background: #0a0a0a !important; }
    `
    // Fix SVG icon fills: path elements have fill="currentColor" which is resolved against
    // the SVG element's color property. DashboardView's scoped CSS sets SVG color to #f0f2f8
    // which overrides our injected fill via currentColor. Solution: set fill="#0d0f14" directly
    // on every SVG path element, bypassing the CSS cascade entirely.
    // Also observe DOM mutations so newly added SVG icons (after SPA navigation) get fixed too.
    try {
      if (document.readyState === 'complete') {
        applyDarkSvgFills()
      } else {
        window.addEventListener('load', () => applyDarkSvgFills(), { once: true })
      }
      observeSvgFills()
    } catch (e) {
      console.error('[flowly] applyDarkSvgFills error:', e)
    }
  } else {
    clearDarkStyle()
    clearDarkSvgFills()
    disconnectSvgObserver()
  }
}

// Fill colors for dark mode: icons on LIGHT backgrounds → black, on DARK backgrounds → white
const ICON_FILL_DARK_BG = '#ffffff'   // white for icons on dark surfaces
const ICON_FILL_LIGHT_BG = '#000000'   // black for icons on light surfaces
// Threshold: if background luminance < 0.35, treat as dark background
function isDarkBackground(r: number, g: number, b: number): boolean {
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance < 0.35
}
function parseRgbToComponents(rgb: string): {r: number, g: number, b: number} | null {
  const m = rgb.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/)
  if (!m) return null
  return { r: parseInt(m[1]), g: parseInt(m[2]), b: parseInt(m[3]) }
}

// Determine icon fill color based on the immediate parent's computed background
function getIconFillForDarkMode(el: Element): string {
  let current: Element | null = el
  for (let depth = 0; depth < 6 && current; depth++) {
    const cs = window.getComputedStyle(current as Element)
    const bg = cs.backgroundColor
    if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
      const rgb = parseRgbToComponents(bg)
      if (rgb) {
        return isDarkBackground(rgb.r, rgb.g, rgb.b) ? ICON_FILL_DARK_BG : ICON_FILL_LIGHT_BG
      }
    }
    current = current.parentElement
  }
  // Default to dark fill if we can't determine
  return ICON_FILL_LIGHT_BG
}

// Set fill on all SVG path elements for dark mode, using smart color based on background
function applyDarkSvgFills() {
  const svgElements = document.querySelectorAll<SVGElement>('svg')
  svgElements.forEach(svg => {
    const paths = svg.querySelectorAll('path')
    if (paths.length === 0) return
    const fill = getIconFillForDarkMode(svg)
    paths.forEach(path => {
      path.setAttribute('fill', fill)
    })
  })
}

// Restore SVG path fill to currentColor (for light mode)
function clearDarkSvgFills() {
  const svgElements = document.querySelectorAll<SVGElement>('svg')
  svgElements.forEach(svg => {
    const paths = svg.querySelectorAll('path')
    paths.forEach(path => {
      if (path.getAttribute('fill') === ICON_FILL_DARK_BG || path.getAttribute('fill') === ICON_FILL_LIGHT_BG) {
        path.setAttribute('fill', 'currentColor')
      }
    })
  })
}

// MutationObserver: fix SVG path fills for any SVGs added after initial theme application
let _svgObserver: MutationObserver | null = null
function observeSvgFills() {
  if (_svgObserver) return
  _svgObserver = new MutationObserver((mutations) => {
    if (!document.documentElement.classList.contains('theme-dark')) return
    for (const mut of mutations) {
      for (const node of mut.addedNodes) {
        if (node instanceof SVGElement) {
          const paths = node.querySelectorAll('path')
          if (paths.length === 0) continue
          const fill = getIconFillForDarkMode(node)
          paths.forEach((p: SVGPathElement) => p.setAttribute('fill', fill))
        } else if (node instanceof Element) {
          const svgs = node.querySelectorAll('svg')
          svgs.forEach(svg => {
            const paths = svg.querySelectorAll('path')
            if (paths.length === 0) return
            const fill = getIconFillForDarkMode(svg)
            paths.forEach((p: SVGPathElement) => p.setAttribute('fill', fill))
          })
        }
      }
    }
  })
  _svgObserver.observe(document.body, { childList: true, subtree: true })
}

function disconnectSvgObserver() {
  if (_svgObserver) {
    _svgObserver.disconnect()
    _svgObserver = null
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

// Expose for debugging / manual invocation in browser console
(window as any).__flowly_fix_svgs = applyDarkSvgFills;
(window as any).__flowly_clear_svgs = clearDarkSvgFills;
