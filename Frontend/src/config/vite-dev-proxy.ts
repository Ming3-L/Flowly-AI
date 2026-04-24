/**
 * Vite 开发服务器代理（集中配置，供 vite.config 引用）。
 */
import type { ProxyOptions } from 'vite'

// Dev backend: default aligns with docs/backend runserver port (8000).
// Override via VITE_DEV_BACKEND, e.g. http://127.0.0.1:8001
const backend = process.env.VITE_DEV_BACKEND || 'http://127.0.0.1:8000'

export const devServerProxy: Record<string, string | ProxyOptions> = {
  '/api': {
    target: backend,
    changeOrigin: true,
    secure: false,
  },
  '/ws': {
    target: backend,
    changeOrigin: true,
    secure: false,
    ws: true,
  },
}
