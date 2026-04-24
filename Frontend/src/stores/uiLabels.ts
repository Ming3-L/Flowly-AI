/**
 * 界面文案：运行时从 ``GET /api/ui-labels`` 加载，数据库由 Django Admin 维护。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/utils/api'

export const useUiLabelsStore = defineStore('uiLabels', () => {
  const locale = ref('zh-CN')
  const labels = ref<Record<string, string>>({})
  const loaded = ref(false)
  const loadError = ref<string | null>(null)
  const updatedAt = ref<string | null>(null)

  const isReady = computed(() => loaded.value)

  function t(key: string, fallback?: string): string {
    const v = labels.value[key]
    if (v !== undefined && v !== '') return v
    if (fallback !== undefined) return fallback
    return key
  }

  async function fetchLabels(loc: string = 'zh-CN'): Promise<void> {
    loadError.value = null
    try {
      const res = await api.get<{ locale: string; labels: Record<string, string>; updated_at?: string | null }>(
        '/ui-labels/',
        {
          params: { locale: loc },
          skipGlobalErrorHandler: true,
        }
      )
      locale.value = res.data.locale || loc
      labels.value = res.data.labels || {}
      updatedAt.value = res.data.updated_at ?? null
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'ui-labels fetch failed'
      loadError.value = msg
      labels.value = {}
    } finally {
      loaded.value = true
    }
  }

  return {
    locale,
    labels,
    loaded,
    loadError,
    updatedAt,
    isReady,
    t,
    fetchLabels,
  }
})
