<template>
  <div class="settings-page">
    <div class="container">
      <h1 class="page-title">账户设置</h1>

      <!-- Profile Info -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <span>个人信息</span>
          </div>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="用户名">{{ auth.user?.username }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ auth.user?.email }}</el-descriptions-item>
          <el-descriptions-item label="注册时间">{{ auth.user?.date_joined?.split('T')[0] }}</el-descriptions-item>
          <el-descriptions-item label="账户状态">
            <el-tag :type="auth.user?.is_active ? 'success' : 'danger'" size="small">
              {{ auth.user?.is_active ? '活跃' : '禁用' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- AI Model Settings -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <span>AI 模型设置</span>
          </div>
        </template>
        <el-form label-width="120px" label-position="left">
          <el-form-item label="AI 模型">
            <el-select v-model="aiModel" placeholder="选择 AI 模型" style="width: 320px">
              <el-option label="GPT-4o (推荐)" value="gpt-4o" />
              <el-option label="GPT-4o Mini" value="gpt-4o-mini" />
              <el-option label="GPT-4 Turbo" value="gpt-4-turbo" />
              <el-option label="GPT-4" value="gpt-4" />
              <el-option label="Claude 3.5 Sonnet" value="claude-3-5-sonnet-20240620" />
              <el-option label="Claude 3 Opus" value="claude-3-opus-20240229" />
              <el-option label="Claude 3 Haiku" value="claude-3-haiku-20240307" />
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

      <!-- API Key Settings -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <span>API Key 设置</span>
          </div>
        </template>
        <el-alert
          title="个人 API Key 优先于系统全局 Key"
          type="info"
          :closable="false"
          style="margin-bottom: 16px"
        />
        <el-form label-width="140px" label-position="left">
          <el-form-item label="OpenAI API Key">
            <el-input
              v-model="apiKey"
              :type="showApiKey ? 'text' : 'password'"
              placeholder="sk-..."
              show-password
              style="width: 400px"
            >
              <template #suffix>
                <el-button
                  size="small"
                  link
                  @click="showApiKey = !showApiKey"
                >
                  <el-icon>
                    <View v-if="!showApiKey" />
                    <Hide v-else />
                  </el-icon>
                </el-button>
              </template>
            </el-input>
            <div class="form-tip">留空使用系统默认 Key</div>
          </el-form-item>

          <el-form-item label="Base URL（可选）">
            <el-input
              v-model="baseUrl"
              placeholder="https://api.openai.com/v1"
              style="width: 400px"
            />
            <div class="form-tip">自定义 API 代理地址（如 OpenAI 兼容接口）</div>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="savingKey" @click="saveApiKey">
              保存 API Key
            </el-button>
            <el-button @click="testApiKey" :loading="testingKey">
              测试连接
            </el-button>
            <el-button @click="apiKey = ''; baseUrl = ''">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Language Settings -->
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

      <!-- Account Actions -->
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
import { View, Hide } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/utils/api'

const auth = useAuthStore()

const aiModel = ref('gpt-4o')
const temperature = ref(0.7)
const maxTokens = ref(4096)
const apiKey = ref('')
const baseUrl = ref('')
const language = ref('zh')
const theme = ref('light')
const showApiKey = ref(false)

const savingModel = ref(false)
const savingKey = ref(false)
const savingPrefs = ref(false)
const testingKey = ref(false)

onMounted(() => {
  if (auth.user) {
    aiModel.value = auth.user.ai_model || 'gpt-4o'
    language.value = auth.user.language || 'zh'
  }
  // Load from localStorage
  const savedPrefs = localStorage.getItem('flowly_preferences')
  if (savedPrefs) {
    try {
      const prefs = JSON.parse(savedPrefs)
      temperature.value = prefs.temperature ?? 0.7
      maxTokens.value = prefs.maxTokens ?? 4096
      theme.value = prefs.theme ?? 'light'
    } catch { /* ignore */ }
  }
})

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

async function saveApiKey() {
  savingKey.value = true
  try {
    const payload: Record<string, string> = {}
    if (apiKey.value) payload.openai_api_key = apiKey.value
    if (baseUrl.value) payload.openai_base_url = baseUrl.value
    if (Object.keys(payload).length > 0) {
      await api.post('/auth/profile/api-key', payload)
    }
    ElMessage.success('API Key 已保存')
    apiKey.value = ''
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingKey.value = false
  }
}

async function testApiKey() {
  testingKey.value = true
  try {
    const res = await api.post('/auth/profile/test-key', {
      openai_api_key: apiKey.value,
      openai_base_url: baseUrl.value || undefined,
    })
    if (res.data.ok) {
      ElMessage.success('连接成功！模型: ' + res.data.model)
    } else {
      ElMessage.error('连接失败: ' + res.data.error)
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '测试连接失败')
  } finally {
    testingKey.value = false
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
    // cancelled
  }
}
</script>

<style scoped>
.settings-page {
  min-height: calc(100vh - 56px);
  background: #ffffff;
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
  color: #000000;
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
  color: #000000;
}

.form-tip {
  font-size: 12px;
  color: #666666;
  margin-top: 4px;
  line-height: 1.4;
}

.danger-card {
  border-color: #e0e0e0;
}
</style>
