/**
 * 第三方登录 (OAuth) Store
 *
 * 提供 GitHub、Google、QQ 三个平台的第三方登录功能。
 * 使用 popup 窗口方案：后端返回授权 URL → 前端打开 popup → 用户授权 → 回调后端 → 返回 JWT
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

export type OAuthProvider = 'github' | 'google' | 'qq'

export interface OAuthConnection {
  id: number
  provider: string
  provider_username: string
  provider_email: string
  created_at: string
}

export const useSocialStore = defineStore('social', () => {
  const auth = useAuthStore()

  // 已连接的第三方账号列表
  const connections = ref<OAuthConnection[]>([])

  // 登录加载状态
  const isLoggingIn = ref<Record<OAuthProvider, boolean>>({
    github: false,
    google: false,
    qq: false,
  })

  // 获取支持的所有 provider
  const supportedProviders = computed<OAuthProvider[]>(() => ['github', 'google', 'qq'])

  // ── 核心：Popup 登录 ────────────────────────────────────────────────────────

  /**
   * 使用 popup 窗口进行第三方登录
   *
   * 流程：
   * 1. 请求后端获取授权 URL
   * 2. 打开 popup 窗口
   * 3. 监听 message 事件接收登录结果
   * 4. 成功后存储 token 并刷新用户信息
   */
  async function loginWithPopup(provider: OAuthProvider): Promise<void> {
    if (isLoggingIn.value[provider]) return

    isLoggingIn.value[provider] = true

    try {
      // 1. 获取授权 URL
      const response = await fetch(`/api/auth/oauth/${provider}/login`)
      const data = await response.json()

      if (!response.ok || !data.auth_url) {
        throw new Error(data.detail || data.message || '获取授权 URL 失败')
      }

      // 2. 打开 popup 窗口
      const width = 600
      const height = 700
      const left = window.screenX + (window.outerWidth - width) / 2
      const top = window.screenY + (window.outerHeight - height) / 2

      const popup = window.open(
        data.auth_url,
        `oauth_${provider}_login`,
        `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no,scrollbars=yes,resizable=yes`
      )

      if (!popup) {
        throw new Error('无法打开登录窗口，请检查浏览器是否阻止了弹窗')
      }

      // 3. 监听消息
      await new Promise<void>((resolve, reject) => {
        const messageHandler = (event: MessageEvent) => {
          const msg = event.data
          if (!msg || typeof msg !== 'object') return

          if (msg.type === 'OAUTH_SUCCESS' && msg.provider === provider) {
            // 登录成功
            handleOAuthSuccess(provider, msg.access, msg.refresh)
            cleanup()
            resolve()
          } else if (msg.type === 'OAUTH_ERROR') {
            cleanup()
            reject(new Error(msg.error || '登录失败'))
          }
        }

        const cleanup = () => {
          window.removeEventListener('message', messageHandler)
          // 关闭 popup
          if (popup && !popup.closed) {
            popup.close()
          }
        }

        // 监听消息
        window.addEventListener('message', messageHandler)

        // 备用：检查 popup 是否关闭（如果 postMessage 失败）
        const checkClosed = setInterval(() => {
          if (popup.closed) {
            cleanup()
            // 如果 localStorage 有 token，说明登录成功了
            const accessToken = localStorage.getItem('flowly_access_token')
            const oauthProvider = localStorage.getItem('flowly_oauth_provider')
            if (accessToken && oauthProvider === provider) {
              handleOAuthSuccess(provider, accessToken, localStorage.getItem('flowly_refresh_token') || '')
              resolve()
            } else {
              reject(new Error('登录已取消'))
            }
            clearInterval(checkClosed)
          }
        }, 500)
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : '登录失败'
      ElMessage.error(message)
      throw error
    } finally {
      isLoggingIn.value[provider] = false
    }
  }

  /**
   * 处理 OAuth 登录成功
   */
  function handleOAuthSuccess(provider: OAuthProvider, access: string, refresh: string) {
    // 存储 token
    localStorage.setItem('flowly_access_token', access)
    if (refresh) {
      localStorage.setItem('flowly_refresh_token', refresh)
    }
    localStorage.setItem('flowly_oauth_provider', provider)

    // 更新 auth store 的 token
    auth.accessToken = access
    auth.refreshToken = refresh || null

    // 清除 oauth_provider 标记
    setTimeout(() => {
      localStorage.removeItem('flowly_oauth_provider')
    }, 5000)

    ElMessage.success(`${getProviderName(provider)} 登录成功`)
  }

  /**
   * 获取 provider 显示名称
   */
  function getProviderName(provider: OAuthProvider): string {
    const names: Record<OAuthProvider, string> = {
      github: 'GitHub',
      google: 'Google',
      qq: 'QQ',
    }
    return names[provider] || provider
  }

  // ── 获取已连接的账号列表 ───────────────────────────────────────────────────

  /**
   * 获取当前用户已绑定的第三方账号列表
   */
  async function fetchConnections() {
    try {
      const response = await fetch('/api/auth/oauth/connections', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('flowly_access_token')}`,
        },
      })

      if (!response.ok) {
        throw new Error('获取连接列表失败')
      }

      const data = await response.json()
      connections.value = data.connections || []
    } catch (error) {
      console.error('fetchConnections error:', error)
      connections.value = []
    }
  }

  // ── 解绑第三方账号 ────────────────────────────────────────────────────────

  /**
   * 解绑指定的第三方账号
   */
  async function unbind(provider: OAuthProvider): Promise<boolean> {
    try {
      const response = await fetch(`/api/auth/oauth/unbind?provider=${provider}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('flowly_access_token')}`,
          'Content-Type': 'application/json',
        },
      })

      const data = await response.json()

      if (!response.ok) {
        ElMessage.error(data.detail || data.message || '解绑失败')
        return false
      }

      // 从本地列表移除
      connections.value = connections.value.filter(c => c.provider !== provider)
      ElMessage.success('解绑成功')
      return true
    } catch (error) {
      ElMessage.error('解绑失败，请稍后重试')
      return false
    }
  }

  // ── 绑定第三方账号 ────────────────────────────────────────────────────────

  /**
   * 绑定第三方账号到当前已登录的用户
   * 注意：这个函数需要在用户已经登录的情况下使用
   */
  async function bindWithPopup(provider: OAuthProvider): Promise<boolean> {
    if (!auth.isAuthenticated) {
      ElMessage.warning('请先登录后再绑定第三方账号')
      return false
    }

    try {
      // 获取授权 URL
      const response = await fetch(`/api/auth/oauth/${provider}/login`)
      const data = await response.json()

      if (!response.ok || !data.auth_url) {
        throw new Error(data.detail || '获取授权 URL 失败')
      }

      // 打开 popup
      const width = 600
      const height = 700
      const left = window.screenX + (window.outerWidth - width) / 2
      const top = window.screenY + (window.outerHeight - height) / 2

      const popup = window.open(
        data.auth_url,
        `oauth_${provider}_bind`,
        `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no,scrollbars=yes,resizable=yes`
      )

      if (!popup) {
        throw new Error('无法打开绑定窗口')
      }

      // 监听消息
      return await new Promise((resolve) => {
        const messageHandler = (event: MessageEvent) => {
          const msg = event.data
          if (!msg || typeof msg !== 'object') return

          if (msg.type === 'OAUTH_SUCCESS') {
            // 绑定不需要处理 token（用户已登录）
            window.removeEventListener('message', messageHandler)
            if (!popup.closed) popup.close()

            // 刷新连接列表
            fetchConnections()
            ElMessage.success(`${getProviderName(provider as OAuthProvider)} 绑定成功`)
            resolve(true)
          } else if (msg.type === 'OAUTH_ERROR') {
            window.removeEventListener('message', messageHandler)
            if (!popup.closed) popup.close()
            ElMessage.error(msg.error || '绑定失败')
            resolve(false)
          }
        }

        window.addEventListener('message', messageHandler)

        // 检查 popup 是否关闭
        const checkClosed = setInterval(() => {
          if (popup.closed) {
            window.removeEventListener('message', messageHandler)
            clearInterval(checkClosed)
            // 用户可能取消了绑定，刷新列表
            fetchConnections()
            resolve(false)
          }
        }, 500)
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : '绑定失败'
      ElMessage.error(message)
      return false
    }
  }

  return {
    // State
    connections,
    isLoggingIn,
    supportedProviders,

    // Actions
    loginWithPopup,
    fetchConnections,
    unbind,
    bindWithPopup,
    getProviderName,
  }
})
