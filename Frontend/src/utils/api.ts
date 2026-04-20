import axios from 'axios'
import { ElMessage } from 'element-plus'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Request interceptor: attach JWT ──────────────────────────────────────────────

api.interceptors.request.use(
  (config) => {
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

    // Show error notification for non-auth errors
    if (error.response?.status !== 401) {
      const detail =
        error.response?.data?.detail ??
        error.response?.data?.message ??
        error.message ??
        'Request failed'
      // Don't show duplicate toast for auth errors (already handled above)
      if (error.response?.status !== 401) {
        ElMessage.error(detail)
      }
    }

    return Promise.reject(error)
  }
)

export default api
