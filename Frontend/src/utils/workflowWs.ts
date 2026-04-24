/**
 * 工作流 WebSocket URL。
 *
 * - **本地开发（import.meta.env.DEV）**：默认直连 ``ws://{当前页 hostname}:8000``，
 *   与浏览器访问的 ``http://{hostname}:5173`` 仅端口不同，不经过 Vite 的 ``/ws`` 代理，
 *   避免各版本代理对 WebSocket 转发不一致导致连接失败。
 * - **生产构建**：走当前站点同源 ``/ws/...``（由 Nginx/Caddy 等与 HTTP 一并反代）。
 * - **任意环境**：可通过 ``VITE_WS_ORIGIN`` 完全指定 WS 源（无末尾斜杠）。
 */
export function buildWorkflowWebSocketUrl(threadId: string): string {
  const configured = (import.meta as any)?.env?.VITE_WS_ORIGIN as string | undefined
  if (configured?.trim()) {
    const base = configured.replace(/\/$/, '')
    const id = String(threadId).trim().toLowerCase()
    return `${base}/ws/workflow/${id}/`
  }

  if (typeof window !== 'undefined') {
    if (import.meta.env.DEV) {
      // 开发环境：优先走 Vite 同源 /ws 代理，避免直连后端端口在部分环境下被拦截/失败
      const id = String(threadId).trim().toLowerCase()
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      return `${protocol}//${window.location.host}/ws/workflow/${id}/`
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const id = String(threadId).trim().toLowerCase()
    return `${protocol}//${window.location.host}/ws/workflow/${id}/`
  }

  const id = String(threadId).trim().toLowerCase()
  return `ws://127.0.0.1:8000/ws/workflow/${id}/`
}
