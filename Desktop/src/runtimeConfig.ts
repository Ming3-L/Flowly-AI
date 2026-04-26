import { app } from 'electron'
import fs from 'node:fs/promises'
import path from 'node:path'

export type DesktopRuntimeConfig = {
  API_BASE_URL?: string
}

const DEFAULT_CONFIG: DesktopRuntimeConfig = {
  API_BASE_URL: '',
}

export async function readLocalConfig(): Promise<DesktopRuntimeConfig> {
  try {
    const p = path.join(app.getPath('userData'), 'flowly.config.json')
    const raw = await fs.readFile(p, 'utf-8')
    const parsed = JSON.parse(raw) as DesktopRuntimeConfig
    return { ...DEFAULT_CONFIG, ...parsed }
  } catch {
    return { ...DEFAULT_CONFIG }
  }
}

