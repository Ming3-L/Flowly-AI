<template>
  <div class="settings-page">
    <div class="container">
      <h1 class="page-title">账户设置</h1>

      <!-- 个人信息 -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <span>个人信息</span>
          </div>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="用户名">{{ auth.user?.username }}</el-descriptions-item>
          <el-descriptions-item label="昵称">
            <el-input v-model="nickname" placeholder="设置昵称（展示用）" style="width: 220px" />
          </el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ auth.user?.email }}</el-descriptions-item>
          <el-descriptions-item label="注册时间">{{ auth.user?.date_joined?.split('T')[0] }}</el-descriptions-item>
          <el-descriptions-item label="账户状态">
            <el-tag :type="auth.user?.is_active ? 'success' : 'danger'" size="small">
              {{ auth.user?.is_active ? '活跃' : '禁用' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <div style="margin-top: 12px; display:flex; gap:12px; align-items:center; flex-wrap:wrap">
          <el-avatar :size="44" :src="auth.user?.avatar_public_url || undefined">
            {{ (auth.user?.nickname || auth.user?.username || '').slice(0, 1).toUpperCase() }}
          </el-avatar>
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            accept="image/*"
            :disabled="uploadingAvatar"
            @change="onAvatarPicked"
          >
            <el-button size="small" :loading="uploadingAvatar">上传头像</el-button>
          </el-upload>
        </div>

        <div v-if="avatarHistory.items.length" style="margin-top: 14px">
          <div style="font-size: 12px; color: #666; margin-bottom: 8px">历史头像（点击切换）</div>
          <div class="avatar-grid">
            <div
              v-for="it in avatarHistory.items"
              :key="it.asset_id"
              class="avatar-item"
              :class="{ active: it.avatar_path === avatarHistory.current_avatar_path }"
            >
              <el-avatar
                :size="46"
                :src="it.avatar_public_url"
                class="avatar-click"
                @click="selectAvatar(it.asset_id)"
              />
              <el-button class="avatar-del" size="small" text type="danger" @click="deleteAvatar(it.asset_id)">
                删除
              </el-button>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 模型设置 -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <span>AI 模型设置</span>
          </div>
        </template>
        <el-form label-width="120px" label-position="left">
          <el-form-item label="AI 模型">
            <el-select v-model="aiModel" placeholder="选择 AI 模型" style="width: 360px" filterable>
              <el-option-group
                v-for="g in groupedModels"
                :key="g.label"
                :label="g.label"
              >
                <el-option
                  v-for="m in g.items"
                  :key="m.key"
                  :label="m.label"
                  :value="m.key"
                >
                  <div style="display:flex;align-items:center;justify-content:space-between;gap:10px">
                    <div style="display:flex;align-items:center;gap:8px;min-width:0">
                      <span style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                        {{ m.label }}
                      </span>
                      <el-tag v-if="m.source === 'user'" size="small" type="warning" effect="plain">用户自有</el-tag>
                    </div>
                    <span style="font-size:11px;color:#999;flex-shrink:0">{{ m.route }}</span>
                  </div>
                </el-option>
              </el-option-group>
            </el-select>
            <div class="form-tip">选择对话使用的 AI 模型</div>
          </el-form-item>

          <el-form-item label="温度参数">
            <el-slider
              v-model="temperature"
              :min="0"
              :max="2"
              :step="0.1"
              :marks="{
                0: '精确',
                1: '平衡',
                2: '创意',
              }"
              style="width: 320px"
            />
            <div class="form-tip">控制输出的随机性（0=确定，2=创意）</div>
          </el-form-item>

          <el-form-item label="最大 Tokens">
            <el-input-number
              v-model="maxTokens"
              :min="256"
              :max="128000"
              :step="256"
              style="width: 200px"
            />
            <div class="form-tip">单次响应的最大 token 数量</div>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="savingModel" @click="saveModel">
              保存模型设置
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 我的模型（用户自定义 + APIKey） -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <span>我的模型（自定义路由/APIKey）</span>
          </div>
        </template>
        <el-alert
          title="这里创建的模型会存放在后端，仅你本人可见；可在聊天/工作流等处手动选择使用，但不会成为系统默认。"
          type="info"
          :closable="false"
          style="margin-bottom: 16px"
        />

        <el-form label-width="120px" label-position="left" style="margin-bottom: 10px">
          <el-form-item label="名称">
            <el-input v-model="presetForm.display_name" placeholder="例如：我的 OpenAI" style="width: 360px" />
          </el-form-item>
          <el-form-item label="线路(route)">
            <el-select v-model="presetForm.route" style="width: 200px">
              <el-option label="openai" value="openai" />
              <el-option label="doubao" value="doubao" />
              <el-option label="claude" value="claude" />
              <el-option label="ollama" value="ollama" />
              <el-option label="vectorengine" value="vectorengine" />
            </el-select>
            <div class="form-tip">决定使用哪个厂商/网关接入；与模型目录一致</div>
          </el-form-item>
          <el-form-item label="模型 ID">
            <el-input v-model="presetForm.model_id" placeholder="例如：gpt-4o / ep-xxxx" style="width: 360px" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="presetForm.api_key" type="password" placeholder="可选（留空表示不用自有密钥）" style="width: 360px" show-password />
          </el-form-item>
          <el-form-item label="Base URL">
            <el-input v-model="presetForm.api_base_url" placeholder="可选：OpenAI 兼容接口地址" style="width: 360px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="creatingPreset" @click="createPreset">新增到“我的模型”</el-button>
          </el-form-item>
        </el-form>

        <el-table :data="userPresets" size="small" border>
          <el-table-column prop="display_name" label="名称" min-width="160" />
          <el-table-column prop="route" label="route" width="110" />
          <el-table-column prop="model_id" label="model_id" min-width="160" />
          <el-table-column label="密钥" width="90">
            <template #default="{ row }">
              <el-tag :type="row.has_custom_credentials ? 'success' : 'info'" size="small">
                {{ row.has_custom_credentials ? '已配置' : '未配置' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" type="danger" text @click="deletePreset(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 语言设置 -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <span>界面设置</span>
          </div>
        </template>
        <el-form label-width="140px" label-position="left">
          <el-form-item label="界面语言">
            <el-select v-model="language" style="width: 200px" @change="handleLanguageChange">
              <el-option label="简体中文" value="zh" />
              <el-option label="English" value="en" />
            </el-select>
          </el-form-item>

          <el-form-item label="界面主题">
            <el-select v-model="theme" style="width: 200px">
              <el-option label="浅色" value="light" />
              <el-option label="深色" value="dark" />
              <el-option label="跟随系统" value="auto" />
            </el-select>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="savingPrefs" @click="savePreferences">
              保存偏好设置
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 账户操作 -->
      <el-card class="section-card danger-card">
        <template #header>
          <div class="section-header">
            <span>账户操作</span>
          </div>
        </template>
        <el-form label-width="140px" label-position="left">
          <el-form-item>
            <el-button type="danger" @click="handleLogout">退出登录</el-button>
            <el-button @click="handleDeleteAccount">注销账户</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import api from '@/utils/api'
import { applyTheme } from '@/utils/theme'

const auth = useAuthStore()

const aiModel = ref('gpt-4o')
const temperature = ref(0.7)
const maxTokens = ref(4096)
const language = ref('zh')
const theme = ref('light')
const nickname = ref('')

const savingModel = ref(false)
const savingPrefs = ref(false)

type AiModelRow = { key: string; label: string; route: string; category_label?: string; category_order?: number; source?: string }
const modelCatalog = ref<AiModelRow[]>([])
const groupedModels = ref<Array<{ label: string; items: AiModelRow[] }>>([])

type UserPresetRow = {
  id: number
  key: string
  display_name: string
  description: string
  route: string
  model_id: string
  is_active: boolean
  has_custom_credentials: boolean
}
const userPresets = ref<UserPresetRow[]>([])
const creatingPreset = ref(false)
const presetForm = ref({
  display_name: '',
  route: 'openai',
  model_id: '',
  api_key: '',
  api_base_url: '',
})

const uploadingAvatar = ref(false)
const avatarHistoryLoading = ref(false)
const avatarHistory = ref<{
  current_avatar_path: string
  items: Array<{ asset_id: number; avatar_path: string; avatar_public_url: string; created_at: string }>
}>({
  current_avatar_path: '',
  items: [],
})

onMounted(() => {
  if (auth.user) {
    aiModel.value = auth.user.ai_model || 'gpt-4o'
    language.value = auth.user.language || 'zh'
    nickname.value = auth.user.nickname || ''
  }
  // 从 localStorage 加载
  const savedPrefs = localStorage.getItem('flowly_preferences')
  if (savedPrefs) {
    try {
      const prefs = JSON.parse(savedPrefs)
      temperature.value = prefs.temperature ?? 0.7
      maxTokens.value = prefs.maxTokens ?? 4096
      theme.value = prefs.theme ?? 'light'
    } catch { /* ignore */ }
  }
  void fetchModelCatalog()
  void fetchUserPresets()
  void fetchAvatarHistory()
})

async function fetchModelCatalog() {
  try {
    const { data } = await api.get<{ models: AiModelRow[] }>('/ai/models')
    modelCatalog.value = Array.isArray(data?.models) ? data.models : []
    // 分组：按 category_label
    const map = new Map<string, AiModelRow[]>()
    for (const m of modelCatalog.value) {
      const label = (m.category_label || '其它').trim()
      if (!map.has(label)) map.set(label, [])
      map.get(label)!.push(m)
    }
    groupedModels.value = Array.from(map.entries()).map(([label, items]) => ({
      label,
      items: items.sort((a, b) => String(a.label).localeCompare(String(b.label))),
    }))
    // 若当前选中不在列表里，回退到第一个
    const ok = modelCatalog.value.some((m) => m.key === aiModel.value)
    if (!ok && modelCatalog.value.length) aiModel.value = modelCatalog.value[0].key
  } catch {
    modelCatalog.value = []
    groupedModels.value = []
  }
}

async function fetchUserPresets() {
  try {
    const { data } = await api.get<UserPresetRow[]>('/ai/user-chat-model-presets')
    userPresets.value = Array.isArray(data) ? data : []
  } catch {
    userPresets.value = []
  }
}

async function createPreset() {
  if (!presetForm.value.display_name.trim() || !presetForm.value.model_id.trim()) {
    ElMessage.warning('请填写名称与模型 ID')
    return
  }
  creatingPreset.value = true
  try {
    await api.post('/ai/user-chat-model-presets', {
      display_name: presetForm.value.display_name.trim(),
      route: presetForm.value.route,
      model_id: presetForm.value.model_id.trim(),
      api_key: presetForm.value.api_key.trim(),
      api_base_url: presetForm.value.api_base_url.trim(),
    })
    ElMessage.success('已新增到“我的模型”')
    presetForm.value.display_name = ''
    presetForm.value.model_id = ''
    presetForm.value.api_key = ''
    presetForm.value.api_base_url = ''
    await fetchModelCatalog()
    await fetchUserPresets()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || e?.response?.data?.detail || '新增失败')
  } finally {
    creatingPreset.value = false
  }
}

async function deletePreset(id: number) {
  try {
    await ElMessageBox.confirm('确定删除该自定义模型吗？', '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await api.delete(`/ai/user-chat-model-presets/${id}`)
    ElMessage.success('已删除')
    await fetchModelCatalog()
    await fetchUserPresets()
  } catch {
    // cancel
  }
}

async function saveModel() {
  savingModel.value = true
  try {
    await auth.updateProfile({
      ai_model: aiModel.value,
      language: language.value,
    })
    localStorage.setItem('flowly_preferences', JSON.stringify({
      temperature: temperature.value,
      maxTokens: maxTokens.value,
      theme: theme.value,
    }))
    ElMessage.success('模型设置已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingModel.value = false
  }
}

async function onAvatarPicked(file: any) {
  const raw: File | undefined = file?.raw
  if (!raw) return
  uploadingAvatar.value = true
  try {
    const fd = new FormData()
    fd.append('file', raw)
    await api.post('/auth/profile/avatar', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
    await auth.fetchCurrentUser()
    ElMessage.success('头像已更新')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.response?.data?.message || '上传失败')
  } finally {
    uploadingAvatar.value = false
  }
}

async function fetchAvatarHistory() {
  avatarHistoryLoading.value = true
  try {
    const { data } = await api.get('/auth/profile/avatars')
    avatarHistory.value = {
      current_avatar_path: String(data?.current_avatar_path || ''),
      items: Array.isArray(data?.items) ? data.items : [],
    }
  } catch {
    avatarHistory.value = { current_avatar_path: '', items: [] }
  } finally {
    avatarHistoryLoading.value = false
  }
}

async function selectAvatar(assetId: number) {
  try {
    await api.post('/auth/profile/avatars/select', { asset_id: assetId })
    await auth.fetchCurrentUser()
    await fetchAvatarHistory()
    ElMessage.success('已切换头像')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.response?.data?.message || '切换失败')
  }
}

async function deleteAvatar(assetId: number) {
  try {
    await ElMessageBox.confirm('删除该历史头像？', '确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api.delete(`/auth/profile/avatars/${assetId}`)
    await auth.fetchCurrentUser()
    await fetchAvatarHistory()
    ElMessage.success('已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

function handleLanguageChange(val: string) {
  language.value = val
  localStorage.setItem('flowly_preferences', JSON.stringify({
    temperature: temperature.value,
    maxTokens: maxTokens.value,
    theme: theme.value,
    language: val,
  }))
}

async function savePreferences() {
  savingPrefs.value = true
  try {
    localStorage.setItem('flowly_preferences', JSON.stringify({
      temperature: temperature.value,
      maxTokens: maxTokens.value,
      theme: theme.value,
      language: language.value,
    }))
    applyTheme(theme.value as any)
    ElMessage.success('偏好设置已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingPrefs.value = false
  }
}

async function handleLogout() {
  await auth.logout()
  ElMessage.success('已退出登录')
}

async function handleDeleteAccount() {
  try {
    await ElMessageBox.confirm(
      '确定要注销账户吗？此操作不可恢复，所有数据将被永久删除。',
      '注销确认',
      {
        confirmButtonText: '注销',
        cancelButtonText: '取消',
        type: 'error',
      }
    )
    await api.delete('/auth/account')
    ElMessage.success('账户已注销')
    auth.logout()
  } catch {
    // 已取消
  }
}
</script>

<style scoped>
.settings-page {
  min-height: calc(100vh - 56px);
  background: var(--app-bg);
  padding: 24px 0;
}

.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--app-text);
  margin: 0 0 20px;
  letter-spacing: -0.3px;
}

.section-card {
  margin-bottom: 16px;
  border-radius: 4px;
}

.section-header {
  font-weight: 600;
  font-size: 15px;
  color: var(--app-text);
}

.form-tip {
  font-size: 12px;
  color: var(--app-text-3);
  margin-top: 4px;
  line-height: 1.4;
}

.danger-card {
  border-color: var(--app-border);
}

.avatar-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.avatar-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 6px;
  border: 1px solid var(--app-border);
  border-radius: 8px;
}

.avatar-item.active {
  border-color: var(--app-text);
}

.avatar-click {
  cursor: pointer;
}

.avatar-del {
  padding: 0 4px;
  height: 18px;
}
</style>
