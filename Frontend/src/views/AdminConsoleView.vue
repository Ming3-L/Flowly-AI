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
          <el-button size="small" type="success" @click="openCatalogEditorForCreate">新增模型</el-button>
        </div>
        <el-table :data="catalogRows" v-loading="modelsLoading" stripe max-height="560" @row-click="onCatalogRowClick">
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
              <el-button link size="small" @click.stop="openCatalogEditorForEdit(row)">编辑</el-button>
              <el-button type="danger" link size="small" @click="deleteCatalog(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="catalogEditorOpen" :title="catalogEditorTitle" width="640px">
          <el-form label-width="120px">
            <el-form-item label="catalog_key">
              <el-input v-model="catalogDraft.catalog_key" :disabled="!!catalogDraft.id" placeholder="如 ark-doubao-seed-2-0-pro" />
            </el-form-item>
            <el-form-item label="名称(label)">
              <el-input v-model="catalogDraft.label" placeholder="展示名" />
            </el-form-item>
            <el-form-item label="接入路由(route)">
              <el-select v-model="catalogDraft.route" style="width: 100%">
                <el-option label="doubao" value="doubao" />
                <el-option label="openai" value="openai" />
                <el-option label="claude" value="claude" />
                <el-option label="ollama" value="ollama" />
                <el-option label="vectorengine" value="vectorengine" />
              </el-select>
            </el-form-item>
            <el-form-item label="model_id">
              <el-input v-model="catalogDraft.model_id" placeholder="如 Doubao-Seed-2.0-pro 或 ep-xxx" />
            </el-form-item>
            <el-form-item label="api_kind">
              <el-select v-model="catalogDraft.api_kind" style="width: 100%">
                <el-option label="ark_chat" value="ark_chat" />
                <el-option label="openspeech" value="openspeech" />
                <el-option label="ark_embedding" value="ark_embedding" />
                <el-option label="ark_rerank" value="ark_rerank" />
              </el-select>
            </el-form-item>
            <el-form-item label="显示到画布模型下拉">
              <el-switch v-model="catalogDraft.show_in_canvas_llm_nodes" />
            </el-form-item>
            <el-form-item label="启用">
              <el-switch v-model="catalogDraft.is_active" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="catalogEditorOpen=false">取消</el-button>
            <el-button type="primary" :loading="catalogSaving" @click="saveCatalogDraft">保存</el-button>
          </template>
        </el-dialog>

        <el-drawer v-model="variantsDrawerOpen" title="二级选项（音色/能力）" size="520px">
          <div v-if="!selectedCatalogRow" class="muted" style="padding: 12px 0">请选择一个模型目录项</div>
          <template v-else>
            <div class="toolbar" style="padding: 0 0 10px 0">
              <el-tag size="small">{{ selectedCatalogRow.catalog_key }}</el-tag>
              <span class="muted" style="margin-left: 8px">{{ selectedCatalogRow.label }}</span>
              <div style="flex:1"></div>
              <el-button size="small" type="primary" :loading="variantsLoading" @click="loadVariants(selectedCatalogRow.id)">
                刷新
              </el-button>
              <el-button size="small" @click="addVariantRow">新增</el-button>
            </div>

            <el-table :data="variantRows" v-loading="variantsLoading" stripe size="small" max-height="480">
              <el-table-column prop="kind" label="kind" width="90" />
              <el-table-column prop="variant_id" label="id" min-width="140" show-overflow-tooltip />
              <el-table-column prop="label" label="名称" min-width="140" show-overflow-tooltip />
              <el-table-column prop="value" label="value" min-width="160" show-overflow-tooltip />
              <el-table-column prop="sort_order" label="排序" width="70" align="right" />
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button link size="small" @click="editVariantRow(row)">编辑</el-button>
                  <el-button link size="small" type="danger" @click="deleteVariantRow(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>

            <el-dialog v-model="variantEditorOpen" title="编辑二级选项" width="560px">
              <el-form label-width="110px">
                <el-form-item label="kind">
                  <el-select v-model="variantDraft.kind" style="width: 100%">
                    <el-option label="voice" value="voice" />
                    <el-option label="capability" value="capability" />
                  </el-select>
                </el-form-item>
                <el-form-item label="variant_id">
                  <el-input v-model="variantDraft.variant_id" placeholder="如 zh_female_vv_uranus_bigtts" />
                </el-form-item>
                <el-form-item label="label">
                  <el-input v-model="variantDraft.label" placeholder="展示名" />
                </el-form-item>
                <el-form-item label="value">
                  <el-input v-model="variantDraft.value" placeholder="实际传给接口的值（speaker/voice_type/resource_id 等）" />
                </el-form-item>
                <el-form-item label="sort_order">
                  <el-input-number v-model="variantDraft.sort_order" :min="-9999" :max="9999" />
                </el-form-item>
                <el-form-item label="config(JSON)">
                  <el-input v-model="variantDraft.config_json" type="textarea" :rows="6" placeholder='{"resource_id":"seed-tts-2.0"}' />
                </el-form-item>
                <el-form-item label="启用">
                  <el-switch v-model="variantDraft.is_active" />
                </el-form-item>
              </el-form>
              <template #footer>
                <el-button @click="variantEditorOpen=false">取消</el-button>
                <el-button type="primary" :loading="variantSaving" @click="saveVariantDraft">保存</el-button>
              </template>
            </el-dialog>
          </template>
        </el-drawer>
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
        <p class="hint smtp-hint">
          <strong>注册/找回密码验证码邮件</strong>仅使用库内
          <code>FLOWLY_SMTP_HOST</code>、<code>FLOWLY_SMTP_PORT</code>（默认 465）、<code>FLOWLY_SMTP_USER</code>（发件箱）、
          <code>FLOWLY_SMTP_PASSWORD</code>（如 QQ 邮箱 SMTP 授权码）；可选
          <code>FLOWLY_SMTP_FROM_EMAIL</code>、<code>FLOWLY_SMTP_USE_SSL</code>/<code>FLOWLY_SMTP_USE_TLS</code>。
          正文由方舟文本模型生成后从上述发件箱发往用户填写的邮箱，请勿依赖 .env 的 EMAIL_*。
        </p>
        <p class="hint smtp-hint">
          <strong>管理员自助注册邀请码</strong>请在库内设置
          <code>FLOWLY_ADMIN_REGISTER_INVITE</code>（管理员）与 <code>FLOWLY_SUPERUSER_REGISTER_INVITE</code>（超管）。
          特殊：若系统还没有任何管理员账号，邀请码 <code>123456789</code> 可用于创建第一个超管（便于初始化后再改为自定义邀请码）。
        </p>
        <div class="secrets-scroll">
          <div v-for="row in secretStatusRows" :key="row.key" class="secret-row">
            <div class="secret-key-block">
              <code class="secret-key">{{ row.key }}</code>
              <span v-if="secretKeyHint(row.key)" class="secret-key-hint">{{ secretKeyHint(row.key) }}</span>
            </div>
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
const selectedCatalogRow = ref<any | null>(null)
const variantsDrawerOpen = ref(false)
const variantsLoading = ref(false)
const variantRows = ref<any[]>([])
const variantEditorOpen = ref(false)
const variantSaving = ref(false)
const catalogEditorOpen = ref(false)
const catalogSaving = ref(false)
const catalogDraft = reactive<any>({
  id: 0,
  catalog_key: '',
  label: '',
  route: 'doubao',
  model_id: '',
  api_kind: 'ark_chat',
  show_in_canvas_llm_nodes: true,
  is_active: true,
})
const catalogEditorTitle = computed(() => (catalogDraft.id ? '编辑模型目录项' : '新增模型目录项'))
const variantDraft = reactive<any>({
  pk: 0,
  kind: 'voice',
  variant_id: '',
  label: '',
  value: '',
  sort_order: 0,
  config_json: '{}',
  is_active: true,
})

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

/** 验证码邮件等专用键的简短说明（其余键留空，仅展示 key） */
function secretKeyHint(key: string): string {
  const hints: Record<string, string> = {
    FLOWLY_SMTP_HOST: 'SMTP 服务器，如 smtp.qq.com',
    FLOWLY_SMTP_PORT: '端口，常用 465（SSL）或 587（STARTTLS）',
    FLOWLY_SMTP_USER: '发件邮箱账号（与 QQ 授权码对应的全邮箱）',
    FLOWLY_SMTP_PASSWORD: 'SMTP 授权码/密码（加密存储）',
    FLOWLY_SMTP_FROM_EMAIL: '可选，发件人显示地址；不填则同 USER',
    FLOWLY_SMTP_USE_SSL: '可选填 1：强制 SSL（一般 465 可留空自动）',
    FLOWLY_SMTP_USE_TLS: '可选填 1：STARTTLS（587 常用）',
    FLOWLY_ADMIN_REGISTER_INVITE: '管理员自助注册邀请码（匹配则注册为管理员）',
    FLOWLY_SUPERUSER_REGISTER_INVITE: '超级管理员自助注册邀请码（匹配则注册为超管）',
  }
  return hints[key] || ''
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

function openCatalogEditorForCreate() {
  catalogDraft.id = 0
  catalogDraft.catalog_key = ''
  catalogDraft.label = ''
  catalogDraft.route = 'doubao'
  catalogDraft.model_id = ''
  catalogDraft.api_kind = 'ark_chat'
  catalogDraft.show_in_canvas_llm_nodes = true
  catalogDraft.is_active = true
  catalogEditorOpen.value = true
}

function openCatalogEditorForEdit(row: any) {
  catalogDraft.id = row.id
  catalogDraft.catalog_key = row.catalog_key || ''
  catalogDraft.label = row.label || ''
  catalogDraft.route = row.route || 'doubao'
  catalogDraft.model_id = row.model_id || ''
  catalogDraft.api_kind = row.api_kind || 'ark_chat'
  catalogDraft.show_in_canvas_llm_nodes = row.show_in_canvas_llm_nodes !== false
  catalogDraft.is_active = row.is_active !== false
  catalogEditorOpen.value = true
}

async function saveCatalogDraft() {
  const ck = String(catalogDraft.catalog_key || '').trim()
  const label = String(catalogDraft.label || '').trim()
  if (!ck) {
    ElMessage.error('catalog_key 不能为空')
    return
  }
  if (!label) {
    ElMessage.error('名称(label) 不能为空')
    return
  }
  catalogSaving.value = true
  try {
    if (!catalogDraft.id) {
      await api.post('/ai/catalog-entries', {
        catalog_key: ck,
        label,
        route: String(catalogDraft.route || 'doubao').trim(),
        model_id: String(catalogDraft.model_id || '').trim(),
        api_kind: String(catalogDraft.api_kind || 'ark_chat').trim(),
        show_in_canvas_llm_nodes: !!catalogDraft.show_in_canvas_llm_nodes,
        is_active: !!catalogDraft.is_active,
      })
    } else {
      await api.patch(`/ai/catalog-entries/${catalogDraft.id}`, {
        label,
        route: String(catalogDraft.route || 'doubao').trim(),
        model_id: String(catalogDraft.model_id || '').trim(),
        api_kind: String(catalogDraft.api_kind || 'ark_chat').trim(),
        show_in_canvas_llm_nodes: !!catalogDraft.show_in_canvas_llm_nodes,
        is_active: !!catalogDraft.is_active,
      })
    }
    catalogEditorOpen.value = false
    await loadModels()
    ElMessage.success('已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    catalogSaving.value = false
  }
}

function onCatalogRowClick(row: any) {
  selectedCatalogRow.value = row
  variantsDrawerOpen.value = true
  loadVariants(row.id)
}

async function loadVariants(entryId: number) {
  if (!isStaff.value) return
  variantsLoading.value = true
  try {
    const res = await api.get(`/ai/catalog-entries/${entryId}/variants`)
    variantRows.value = res.data ?? []
  } catch {
    variantRows.value = []
    ElMessage.error('加载二级选项失败')
  } finally {
    variantsLoading.value = false
  }
}

function addVariantRow() {
  variantDraft.pk = 0
  variantDraft.kind = 'voice'
  variantDraft.variant_id = ''
  variantDraft.label = ''
  variantDraft.value = ''
  variantDraft.sort_order = 0
  variantDraft.config_json = '{}'
  variantDraft.is_active = true
  variantEditorOpen.value = true
}

function editVariantRow(row: any) {
  variantDraft.pk = row.id
  variantDraft.kind = row.kind || 'voice'
  variantDraft.variant_id = row.variant_id || ''
  variantDraft.label = row.label || ''
  variantDraft.value = row.value || ''
  variantDraft.sort_order = row.sort_order ?? 0
  variantDraft.is_active = !!row.is_active
  variantDraft.config_json = JSON.stringify(row.config ?? {}, null, 2)
  variantEditorOpen.value = true
}

async function saveVariantDraft() {
  const entry = selectedCatalogRow.value
  if (!entry) return
  let cfg: any = {}
  try {
    cfg = JSON.parse(String(variantDraft.config_json || '{}'))
  } catch {
    ElMessage.error('config JSON 解析失败')
    return
  }
  variantSaving.value = true
  try {
    if (!variantDraft.pk) {
      await api.post(`/ai/catalog-entries/${entry.id}/variants`, {
        kind: variantDraft.kind,
        variant_id: variantDraft.variant_id,
        label: variantDraft.label,
        value: variantDraft.value,
        sort_order: variantDraft.sort_order,
        config: cfg,
        is_active: variantDraft.is_active,
      })
    } else {
      await api.patch(`/ai/catalog-entries/${entry.id}/variants/${variantDraft.pk}`, {
        kind: variantDraft.kind,
        variant_id: variantDraft.variant_id,
        label: variantDraft.label,
        value: variantDraft.value,
        sort_order: variantDraft.sort_order,
        config: cfg,
        is_active: variantDraft.is_active,
      })
    }
    variantEditorOpen.value = false
    await loadVariants(entry.id)
    ElMessage.success('已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    variantSaving.value = false
  }
}

async function deleteVariantRow(row: any) {
  const entry = selectedCatalogRow.value
  if (!entry) return
  try {
    await ElMessageBox.confirm(`确认删除二级选项「${row.label || row.variant_id}」？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api.delete(`/ai/catalog-entries/${entry.id}/variants/${row.id}`)
    await loadVariants(entry.id)
    ElMessage.success('已删除')
  } catch {
    ElMessage.error('删除失败')
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

.smtp-hint code {
  font-size: 11px;
  padding: 0 3px;
  background: var(--app-surface-alt, rgba(0, 0, 0, 0.06));
  border-radius: 4px;
}

.secret-key-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.secret-key-hint {
  font-size: 11px;
  color: var(--app-text-2);
  line-height: 1.35;
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
