/**
 * Vite 开发服务器代理（集中配置，供 vite.config 引用）。
 */
import type { ProxyOptions } from 'vite'

// Dev backend: use 8001 by default to avoid port conflicts
const backend = 'http://127.0.0.1:8001'

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
