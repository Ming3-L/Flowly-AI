<template>
  <div class="admin-console-view">
    <div class="page-header">
      <h2 class="page-title">后台管理</h2>
      <p class="page-desc">AI 模型目录、接入密钥、用户与媒体资源（仅管理员）</p>
    </div>

    <el-empty
      v-if="!isStaff"
      description="当前账号无权限访问后台"
      style="padding: 48px 0"
    />

    <el-tabs v-else v-model="activeTab" class="admin-tabs" @tab-change="onTabChange">
      <el-tab-pane label="AI 模型目录" name="models">
        <div class="toolbar">
          <el-button type="primary" size="small" :icon="Refresh" :loading="modelsLoading" @click="loadModels">
            刷新
          </el-button>
        </div>
        <el-table :data="catalogRows" v-loading="modelsLoading" stripe max-height="560">
          <el-table-column prop="catalog_key" label="Key" min-width="140" show-overflow-tooltip />
          <el-table-column prop="label" label="名称" min-width="120" />
          <el-table-column prop="route" label="接入路由" width="100" />
          <el-table-column prop="model_id" label="model_id" min-width="160" show-overflow-tooltip />
          <el-table-column prop="api_kind" label="api_kind" width="110" />
          <el-table-column label="启用" width="88" align="center">
            <template #default="{ row }">
              <el-switch
                :model-value="row.is_active"
                :loading="row._toggling"
                @change="onCatalogActiveChange(row, $event)"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center" fixed="right">
            <template #default="{ row }">
              <el-button type="danger" link size="small" @click="deleteCatalog(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="接入配置 (密钥)" name="secrets">
        <div class="toolbar">
          <el-button size="small" type="primary" :loading="secretsLoading" @click="loadSecretsStatus">
            刷新状态
          </el-button>
          <el-button size="small" :loading="secretsSaving" @click="saveSecretPatches">保存已填项</el-button>
          <el-button size="small" @click="importSecretsFromEnv(false)">从环境变量导入</el-button>
          <el-button size="small" type="danger" plain @click="importSecretsFromEnv(true)">
            替换导入（先清空库内）
          </el-button>
        </div>
        <p class="hint">
          库内配置优先于服务器 .env。仅保存您在输入框中新填写的内容；「清除库内项」可恢复为环境变量。
        </p>
        <div class="secrets-scroll">
          <div v-for="row in secretStatusRows" :key="row.key" class="secret-row">
            <code class="secret-key">{{ row.key }}</code>
            <div class="secret-tags">
              <el-tag size="small">{{ sourceLabel(row.winning_source) }}</el-tag>
              <el-tag v-if="row.is_effective_non_empty" size="small" type="success">有值</el-tag>
            </div>
            <el-input
              v-model="secretDrafts[row.key]"
              :type="isSensitiveKey(row.key) ? 'password' : 'text'"
              :placeholder="isSensitiveKey(row.key) ? '填写新密钥…' : '填写新值…'"
              clearable
              class="secret-input"
            />
            <el-button size="small" link type="danger" @click="clearDbSecret(row.key)">清除库内项</el-button>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="用户" name="users">
        <el-table :data="userRows" v-loading="usersLoading" stripe max-height="560">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="username" label="用户名" min-width="120" />
          <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
          <el-table-column label="角色" width="120">
            <template #default="{ row }">
              <el-tag v-if="row.is_superuser" type="danger" size="small">超管</el-tag>
              <el-tag v-else-if="row.is_staff" type="warning" size="small">管理员</el-tag>
              <span v-else class="muted">用户</span>
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="激活" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="date_joined" label="注册时间" min-width="170" />
        </el-table>
        <div class="pager">
          <el-pagination
            layout="prev, pager, next, total"
            :total="usersTotal"
            :page-size="usersPageSize"
            v-model:current-page="usersPage"
            @current-change="loadUsers"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="媒体资源" name="media">
        <div class="toolbar">
          <el-select v-model="mediaKind" placeholder="类型" clearable style="width: 120px" @change="loadMedia">
            <el-option label="图片" value="image" />
            <el-option label="音频" value="audio" />
            <el-option label="视频" value="video" />
            <el-option label="文件" value="file" />
            <el-option label="头像" value="avatar" />
          </el-select>
          <el-button size="small" :icon="Refresh" :loading="mediaLoading" @click="loadMedia">刷新</el-button>
        </div>
        <el-table :data="mediaRows" v-loading="mediaLoading" stripe max-height="520">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="username" label="用户" width="120" />
          <el-table-column prop="kind" label="类型" width="90" />
          <el-table-column prop="size_bytes" label="大小" width="100" align="right">
            <template #default="{ row }">{{ formatBytes(row.size_bytes) }}</template>
          </el-table-column>
          <el-table-column prop="mime" label="MIME" min-width="120" show-overflow-tooltip />
          <el-table-column prop="original_name" label="文件名" min-width="140" show-overflow-tooltip />
          <el-table-column prop="rel_path" label="相对路径" min-width="200" show-overflow-tooltip />
          <el-table-column prop="created_at" label="创建时间" width="170" />
        </el-table>
        <div class="pager">
          <el-pagination
            layout="prev, pager, next, total"
            :total="mediaTotal"
            :page-size="mediaPageSize"
            v-model:current-page="mediaPage"
            @current-change="loadMedia"
          />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import api from '@/utils/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const isStaff = computed(() => !!(auth.user && (auth.user.is_staff || auth.user.is_superuser)))

const activeTab = ref<string>('models')

const modelsLoading = ref(false)
const catalogRows = ref<any[]>([])

const usersLoading = ref(false)
const userRows = ref<any[]>([])
const usersTotal = ref(0)
const usersPage = ref(1)
const usersPageSize = 20

const mediaLoading = ref(false)
const mediaRows = ref<any[]>([])
const mediaTotal = ref(0)
const mediaPage = ref(1)
const mediaPageSize = 20
const mediaKind = ref<string | undefined>(undefined)

const secretsLoading = ref(false)
const secretsSaving = ref(false)
const secretStatusRows = ref<
  Array<{ key: string; winning_source: string; is_effective_non_empty: boolean }>
>([])
const secretDrafts = reactive<Record<string, string>>({})

function sourceLabel(src: string): string {
  const m: Record<string, string> = {
    database: '库内',
    environment: '环境变量',
    local_file: '本地 secrets 文件',
    default: '默认/未设',
  }
  return m[src] || src
}

function isSensitiveKey(key: string): boolean {
  const u = key.toUpperCase()
  if (u.includes('PASSWORD')) return true
  if (u.includes('API_KEY') || u.endsWith('_KEY')) return true
  if (u.includes('TOKEN') || u.includes('SECRET')) return true
  return false
}

async function loadSecretsStatus() {
  if (!isStaff.value) return
  secretsLoading.value = true
  try {
    const res = await api.get('/admin/ai-provider-secrets/status')
    secretStatusRows.value = res.data?.items ?? []
    for (const r of secretStatusRows.value) {
      if (secretDrafts[r.key] === undefined) secretDrafts[r.key] = ''
    }
  } catch {
    secretStatusRows.value = []
    ElMessage.error('加载接入配置状态失败')
  } finally {
    secretsLoading.value = false
  }
}

async function saveSecretPatches() {
  const entries: Record<string, string> = {}
  for (const r of secretStatusRows.value) {
    const v = (secretDrafts[r.key] || '').trim()
    if (v) entries[r.key] = v
  }
  if (Object.keys(entries).length === 0) {
    ElMessage.info('没有需要保存的新值（仅保存非空输入框）')
    return
  }
  secretsSaving.value = true
  try {
    await api.patch('/admin/ai-provider-secrets', { entries })
    for (const k of Object.keys(entries)) secretDrafts[k] = ''
    ElMessage.success('已保存')
    await loadSecretsStatus()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    secretsSaving.value = false
  }
}

async function clearDbSecret(key: string) {
  try {
    await api.patch('/admin/ai-provider-secrets', { entries: { [key]: '' } })
    secretDrafts[key] = ''
    ElMessage.success('已清除库内覆盖')
    await loadSecretsStatus()
  } catch {
    ElMessage.error('清除失败')
  }
}

async function importSecretsFromEnv(replace: boolean) {
  const tip = replace
    ? '将清空数据库中已有接入项，再写入当前进程环境变量中的非空项。确定？'
    : '将把当前进程环境变量中的非空项合并写入数据库。确定？'
  try {
    await ElMessageBox.confirm(tip, '导入', { type: replace ? 'warning' : 'info' })
  } catch {
    return
  }
  secretsSaving.value = true
  try {
    await api.post('/admin/ai-provider-secrets/import-from-env', { replace })
    ElMessage.success('导入完成')
    await loadSecretsStatus()
  } catch {
    ElMessage.error('导入失败')
  } finally {
    secretsSaving.value = false
  }
}

function formatBytes(n: number): string {
  const kb = 1024
  const mb = kb * kb
  if (n >= mb) return `${(n / mb).toFixed(2)} MB`
  if (n >= kb) return `${(n / kb).toFixed(1)} KB`
  return `${n} B`
}

async function loadModels() {
  if (!isStaff.value) return
  modelsLoading.value = true
  try {
    const res = await api.get('/ai/catalog-entries')
    catalogRows.value = (res.data || []).map((r: any) => ({ ...r, _toggling: false }))
  } catch {
    catalogRows.value = []
    ElMessage.error('加载模型目录失败')
  } finally {
    modelsLoading.value = false
  }
}

function onCatalogActiveChange(row: any, val: string | number | boolean) {
  toggleCatalogActive(row, Boolean(val))
}

async function toggleCatalogActive(row: any, val: boolean) {
  row._toggling = true
  try {
    await api.patch(`/ai/catalog-entries/${row.id}`, { is_active: val })
    row.is_active = val
    ElMessage.success(val ? '已启用' : '已停用')
  } catch {
    ElMessage.error('更新失败')
  } finally {
    row._toggling = false
  }
}

async function deleteCatalog(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除目录项「${row.catalog_key}」？`, '确认', { type: 'warning' })
    await api.delete(`/ai/catalog-entries/${row.id}`)
    ElMessage.success('已删除')
    await loadModels()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

async function loadUsers() {
  if (!isStaff.value) return
  usersLoading.value = true
  try {
    const res = await api.get('/admin/users', {
      params: { page: usersPage.value, page_size: usersPageSize },
    })
    userRows.value = res.data?.items ?? []
    usersTotal.value = res.data?.total ?? 0
  } catch {
    userRows.value = []
    ElMessage.error('加载用户列表失败')
  } finally {
    usersLoading.value = false
  }
}

async function loadMedia() {
  if (!isStaff.value) return
  mediaLoading.value = true
  try {
    const res = await api.get('/admin/media', {
      params: {
        page: mediaPage.value,
        page_size: mediaPageSize,
        kind: mediaKind.value || undefined,
      },
    })
    mediaRows.value = res.data?.items ?? []
    mediaTotal.value = res.data?.total ?? 0
  } catch {
    mediaRows.value = []
    ElMessage.error('加载媒体列表失败')
  } finally {
    mediaLoading.value = false
  }
}

function onTabChange(name: string | number) {
  const n = String(name)
  if (n === 'users') loadUsers()
  if (n === 'media') loadMedia()
  if (n === 'secrets') loadSecretsStatus()
}

onMounted(() => {
  if (isStaff.value) loadModels()
})
</script>

<style scoped lang="scss">
.admin-console-view {
  padding: 20px 24px 40px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 16px;
}

.page-title {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 700;
  color: var(--app-text);
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: var(--app-text-2);
}

.admin-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 12px;
  }
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.muted {
  color: var(--app-text-2);
  font-size: 13px;
}

.hint {
  font-size: 12px;
  color: var(--app-text-2);
  margin: 0 0 12px;
  line-height: 1.5;
}

.secrets-scroll {
  max-height: 520px;
  overflow-y: auto;
  border: 1px solid var(--app-border);
  border-radius: 8px;
  padding: 8px 12px;
  background: var(--app-surface);
}

.secret-row {
  display: grid;
  grid-template-columns: minmax(180px, 1.1fr) auto 1.4fr auto;
  gap: 10px;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);

  &:last-child {
    border-bottom: none;
  }
}

.secret-key {
  font-size: 12px;
  word-break: break-all;
  color: var(--app-text);
}

.secret-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.secret-input {
  min-width: 0;
}

@media (max-width: 900px) {
  .secret-row {
    grid-template-columns: 1fr;
  }
}
</style>
