import { app, BrowserWindow } from 'electron'
import express from 'express'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { readLocalConfig } from './runtimeConfig'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

function resolveFrontendDist(): string {
  // When running from source: repoRoot/Frontend/dist
  // When packaged: place Frontend dist next to Desktop/ (user can copy it) — we also fallback to resources path.
  const repoRoot = path.resolve(__dirname, '../../..')
  const cand1 = path.join(repoRoot, 'Frontend', 'dist')
  const cand2 = path.join(process.resourcesPath || '', 'frontend_dist')
  return cand1 || cand2
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 640,
    webPreferences: {
      contextIsolation: true,
      sandbox: false,
    },
  })

  const distDir = resolveFrontendDist()
  const server = express()

  // Dynamic runtime config (overrides build-time VITE_API_BASE_URL)
  server.get('/runtime-config.js', async (_req, res) => {
    const cfg = await readLocalConfig()
    const apiBase =
      process.env.FLOWLY_API_BASE_URL?.toString().trim() ||
      cfg.API_BASE_URL?.toString().trim() ||
      ''
    res.type('application/javascript').send(
      `window.__FLOWLY_RUNTIME__ = { API_BASE_URL: ${JSON.stringify(apiBase)} };`,
    )
  })

  server.use(express.static(distDir))

  const listener = server.listen(0, '127.0.0.1', async () => {
    const addr = listener.address()
    if (!addr || typeof addr === 'string') return
    const url = `http://127.0.0.1:${addr.port}/index.html`
    await win.loadURL(url)
  })
}

app.whenReady().then(async () => {
  await createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) void createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

