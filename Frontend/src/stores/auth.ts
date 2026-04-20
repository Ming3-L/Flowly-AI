import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/utils/api'
import router from '@/router'

export interface UserProfile {
  id: number
  username: string
  email: string
  ai_model: string
  language: string
  openai_base_url: string
  is_active: boolean
  date_joined: string
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('flowly_access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('flowly_refresh_token'))
  const user = ref<UserProfile | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)

  // ── Register ────────────────────────────────────────────────────────────────
  async function register(payload: {
    username: string
    email: string
    password: string
    password_confirm: string
  }) {
    const res = await api.post('/auth/register', payload)
    return res.data
  }

  // ── Login ────────────────────────────────────────────────────────────────
  async function login(username: string, password: string) {
    const res = await api.post('/auth/login', { username, password })
    const data = res.data
    accessToken.value = data.access
    refreshToken.value = data.refresh ?? null
    localStorage.setItem('flowly_access_token', data.access)
    if (data.refresh) {
      localStorage.setItem('flowly_refresh_token', data.refresh)
    }
    await fetchCurrentUser()
  }

  // ── Logout ──────────────────────────────────────────────────────────────
  async function logout() {
    if (refreshToken.value) {
      try {
        await api.post('/auth/logout', { refresh: refreshToken.value })
      } catch {
        // ignore
      }
    }
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('flowly_access_token')
    localStorage.removeItem('flowly_refresh_token')
    router.push('/login')
  }

  // ── Fetch current user ──────────────────────────────────────────────────
  async function fetchCurrentUser() {
    if (!accessToken.value) return
    try {
      const res = await api.get('/auth/me')
      user.value = res.data
    } catch {
      // token invalid
      accessToken.value = null
      refreshToken.value = null
      localStorage.removeItem('flowly_access_token')
      localStorage.removeItem('flowly_refresh_token')
      user.value = null
    }
  }

  // ── Update profile ───────────────────────────────────────────────────────
  async function updateProfile(payload: Partial<Pick<UserProfile, 'ai_model' | 'language'>>) {
    const res = await api.put('/auth/profile', payload)
    user.value = { ...user.value, ...res.data } as UserProfile
    return res.data
  }

  // ── Set API Key ────────────────────────────────────────────────────────
  async function setApiKey(apiKey: string) {
    const res = await api.post('/auth/profile/api-key', { openai_api_key: apiKey })
    user.value = { ...user.value, ...res.data } as UserProfile
    return res.data
  }

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    register,
    login,
    logout,
    fetchCurrentUser,
    updateProfile,
    setApiKey,
  }
})
