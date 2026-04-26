import axios from 'axios'
import { ElMessage } from 'element-plus'

function getRuntimeBaseUrl(): string {
  const rt = (globalThis as any)?.__FLOWLY_RUNTIME__
  const v = (rt?.API_BASE_URL ?? '').toString().trim()
  return v
}

declare module 'axios' {
  // Project-level extensions used by interceptors/callers.
  export interface AxiosRequestConfig {
    /** Skip global toast error handling for this request. */
    skipGlobalErrorHandler?: boolean
    /** Internal retry flag for refresh flow. */
    _retry?: boolean
  }
}

const BASE_URL = getRuntimeBaseUrl() || import.meta.env.VITE_API_BASE_URL || '/api'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
})

// ── Request interceptor: attach JWT ──────────────────────────────────────────────

api.interceptors.request.use(
  (config) => {
    // Let the browser set multipart boundary for FormData.
    // If we keep application/json here, Django won't see request.FILES.
    const d: any = (config as any).data
    if (typeof FormData !== 'undefined' && d instanceof FormData) {
      // Axios may normalize header keys; defensively clear both.
      delete (config.headers as any)?.['Content-Type']
      delete (config.headers as any)?.['content-type']
    }
    const token = localStorage.getItem('flowly_access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── Response interceptor: handle 401 with token refresh ────────────────────────

let _isRefreshing = false
let _refreshQueue: Array<(token: string) => void> = []

function processRefreshQueue(token: string) {
  _refreshQueue.forEach((cb) => cb(token))
  _refreshQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // 401 — attempt token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (_isRefreshing) {
        // Queue this request until refresh completes
        return new Promise((resolve) => {
          _refreshQueue.push((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(api(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      _isRefreshing = true

      const refreshToken = localStorage.getItem('flowly_refresh_token')
      if (!refreshToken) {
        _isRefreshing = false
        // No refresh token — force logout
        localStorage.removeItem('flowly_access_token')
        return Promise.reject(error)
      }

      try {
        const res = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh: refreshToken,
        })

        const newAccessToken = res.data.access
        const newRefreshToken = res.data.refresh ?? refreshToken

        localStorage.setItem('flowly_access_token', newAccessToken)
        if (newRefreshToken !== refreshToken) {
          localStorage.setItem('flowly_refresh_token', newRefreshToken)
        }

        // Update Authorization header for this request
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`

        // Retry queued requests
        processRefreshQueue(newAccessToken)

        _isRefreshing = false

        // Retry the original request
        return api(originalRequest)
      } catch (refreshError) {
        _isRefreshing = false
        processRefreshQueue('')
        localStorage.removeItem('flowly_access_token')
        localStorage.removeItem('flowly_refresh_token')
        return Promise.reject(refreshError)
      }
    }

    // Show error notification for non-auth errors (unless caller opts out)
    if (error.response?.status !== 401 && !originalRequest?.skipGlobalErrorHandler) {
      const detail =
        error.response?.data?.detail ??
        error.response?.data?.message ??
        error.message ??
        'Request failed'
      ElMessage.error(detail)
    }

    return Promise.reject(error)
  }
)

export default api
