<template>
  <el-dialog
    v-model="open"
    :title="title"
    width="720px"
    destroy-on-close
    append-to-body
  >
    <div class="body">
      <div class="row">
        <div class="col">
          <div class="label">AI 模型</div>
          <el-select v-model="form.model_key" filterable class="w" placeholder="选择模型">
            <el-option-group
              v-for="(grp, gidx) in modelOptionGroups"
              :key="`pem-${gidx}-${grp.label}`"
              :label="grp.label"
            >
              <el-option
                v-for="m in grp.rows"
                :key="m.key"
                :label="m.label"
                :value="m.key"
              >
                <div class="opt-main">
                  {{ m.label }}
                  <span v-if="m.has_custom_credentials" class="own-key">自有密钥</span>
                </div>
                <div class="opt-sub">{{ m.scope_summary || m.description }}</div>
              </el-option>
            </el-option-group>
          </el-select>
        </div>
      </div>

      <div class="row">
        <div class="col">
          <div class="label">原提示词</div>
          <el-input
            v-model="form.raw_prompt"
            type="textarea"
            :rows="6"
            placeholder="输入要加工的提示词…"
          />
        </div>
      </div>

      <div class="row">
        <div class="col">
          <div class="label">加工要求（可选）</div>
          <el-input
            v-model="form.instruction"
            type="textarea"
            :rows="3"
            placeholder="例如：更专业、更结构化、强调输入输出…"
          />
        </div>
      </div>

      <div class="actions">
        <el-button :loading="loading" type="primary" @click="generate">生成</el-button>
        <el-button :disabled="loading" @click="resetCandidates">清空结果</el-button>
      </div>

      <div v-if="candidates.length" class="candidates">
        <div class="label">候选结果（选择一个）</div>
        <el-radio-group v-model="selected" class="w">
          <div v-for="(c, idx) in candidates" :key="idx" class="candidate">
            <el-radio :value="c">方案 {{ idx + 1 }}</el-radio>
            <el-input :model-value="c" type="textarea" :rows="4" readonly />
          </div>
        </el-radio-group>
      </div>
    </div>

    <template #footer>
      <el-button @click="open = false" :disabled="loading">取消</el-button>
      <el-button
        type="primary"
        :disabled="!selected || loading"
        @click="confirm"
      >
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

type CatalogModel = {
  key: string
  label: string
  description: string
  route: string
  source?: string
  category?: string
  category_label?: string
  category_order?: number
  scopes?: string[]
  scope_summary?: string
  has_custom_credentials?: boolean
}

type ModelOptionGroup = { label: string; order: number; rows: CatalogModel[] }

const open = defineModel<boolean>({ required: true })

const props = defineProps<{
  title?: string
  workflowId?: number | null
  clientNodeId?: string
  nodeType?: string
  field: string
  initialValue: string
  /** 与画布节点 modelKey 对齐，默认豆包预设 */
  modelKey?: string
}>()

const emit = defineEmits<{
  (e: 'confirm', value: string): void
}>()

const title = computed(() => props.title ?? 'AI 加工')

const models = ref<CatalogModel[]>([])
const modelOptionGroups = computed<ModelOptionGroup[]>(() => {
  const rows = models.value
  const map = new Map<string, ModelOptionGroup>()
  for (const row of rows) {
    const cid = String(row.category ?? 'other')
    const lab = row.category_label || '其它'
    const key = `${cid}@@${lab}`
    const order = typeof row.category_order === 'number' ? row.category_order : 999
    const g = map.get(key)
    if (g) g.rows.push(row)
    else map.set(key, { label: lab, order, rows: [row] })
  }
  return [...map.values()].sort((a, b) => a.order - b.order || a.label.localeCompare(b.label))
})
const loading = ref(false)
const candidates = ref<string[]>([])
const selected = ref<string>('')

const form = reactive({
  workflow_id: props.workflowId ?? null,
  client_node_id: props.clientNodeId ?? '',
  node_type: props.nodeType ?? '',
  field: props.field,
  raw_prompt: props.initialValue ?? '',
  instruction: '',
  model_key: 'doubao-default',
})

watch(
  () => open.value,
  async (v) => {
    if (!v) return
    candidates.value = []
    selected.value = ''
    form.workflow_id = props.workflowId ?? null
    form.client_node_id = props.clientNodeId ?? ''
    form.node_type = props.nodeType ?? ''
    form.field = props.field
    form.raw_prompt = props.initialValue ?? ''
    form.instruction = ''
    form.model_key = (props.modelKey || '').trim() || 'doubao-default'
    await ensureModels()
    if (models.value.length && !models.value.some((x) => x.key === form.model_key)) {
      form.model_key = models.value[0].key
    }
  }
)

async function ensureModels() {
  if (models.value.length) return
  try {
    const res = await api.get<{ models: CatalogModel[] }>('/ai/models')
    models.value = res.data.models ?? []
    if (!models.value.length) {
      ElMessage.warning('未获取到可用模型列表')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message ?? '获取模型列表失败')
  }
}

function resetCandidates() {
  candidates.value = []
  selected.value = ''
}

async function generate() {
  const raw = String(form.raw_prompt ?? '').trim()
  if (!raw) {
    ElMessage.warning('请先输入原提示词')
    return
  }
  const mk = String(form.model_key ?? '').trim()
  if (!mk) {
    ElMessage.warning('请选择 AI 模型')
    return
  }
  loading.value = true
  try {
    const res = await api.post<{
      record_id: number
      candidates: string[]
      suggested: string
    }>('/prompt-tools/enhance', {
      workflow_id: form.workflow_id,
      client_node_id: form.client_node_id,
      node_type: form.node_type,
      field: form.field,
      raw_prompt: raw,
      instruction: String(form.instruction ?? ''),
      model_key: mk,
    })
    candidates.value = Array.isArray(res.data.candidates) ? res.data.candidates : []
    selected.value = res.data.suggested || candidates.value[0] || ''
    if (!candidates.value.length) {
      ElMessage.warning('未返回候选结果')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message ?? '生成失败')
  } finally {
    loading.value = false
  }
}

function confirm() {
  const v = String(selected.value ?? '').trim()
  if (!v) return
  emit('confirm', v)
  open.value = false
}
</script>

<style scoped lang="scss">
.body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.row {
  display: flex;
  gap: 12px;
}

.col {
  flex: 1;
}

.w {
  width: 100%;
}

.label {
  font-size: 12px;
  font-weight: 600;
  color: #333;
  margin-bottom: 6px;
}

.actions {
  display: flex;
  gap: 12px;
}

.candidates {
  margin-top: 6px;
}

.candidate {
  margin-bottom: 12px;
}

.opt-main {
  font-size: 13px;
}

.opt-sub {
  font-size: 11px;
  color: #888;
  line-height: 1.3;
}

.own-key {
  margin-left: 6px;
  font-size: 11px;
  color: #409eff;
}
</style>
