<template>
  <div
    ref="fabRef"
    class="wf-guide-fab"
    :style="{ right: `${pos.right}px`, bottom: `${pos.bottom}px` }"
    @pointerdown="onFabPointerDown"
    @dblclick.stop="openDrawer"
  >
    <button type="button" class="fab-inner" aria-label="工作流助手">
      <img v-show="logoOk" class="fab-logo" src="/logo.png" alt="" @error="logoOk = false" />
      <span v-if="!logoOk" class="fab-fallback">F</span>
    </button>
  </div>

  <el-drawer
    v-model="drawerOpen"
    title="工作流助手"
    direction="rtl"
    size="400px"
    append-to-body
    class="wf-guide-drawer"
  >
    <div class="drawer-body">
      <div class="model-row">
        <el-select v-model="form.model_key" filterable size="small" class="grow" placeholder="AI 模型">
          <el-option-group
            v-for="(grp, gidx) in modelOptionGroups"
            :key="`wfg-${gidx}-${grp.label}`"
            :label="grp.label"
          >
            <el-option
              v-for="m in grp.rows"
              :key="m.key"
              :label="m.label"
              :value="m.key"
            >
              <div class="m-title">{{ m.label }}</div>
              <div class="m-sub">{{ m.scope_summary || m.description }}</div>
            </el-option>
          </el-option-group>
        </el-select>
      </div>

      <div ref="scrollRef" class="messages">
        <div v-for="(m, i) in chatMessages" :key="i" class="bubble" :class="m.role">
          <div class="role">{{ m.role === 'user' ? '我' : '助手' }}</div>
          <div class="text">{{ m.content }}</div>
        </div>
      </div>

      <div class="composer">
        <el-input
          v-model="draft"
          type="textarea"
          :rows="3"
          placeholder="输入问题，Enter 发送（Shift+Enter 换行）"
          @keydown="onDraftKeydown"
        />
        <el-button type="primary" size="small" :loading="sending" @click="send">发送</el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

type CatalogModel = {
  key: string
  label: string
  description: string
  route: string
  /** catalog | project | user */
  source?: string
  api_kind?: string
  show_in_canvas_llm_nodes?: boolean
  category?: string
  category_label?: string
  category_order?: number
  scope_summary?: string
}

type ModelOptionGroup = { label: string; order: number; rows: CatalogModel[] }

type ChatMsg = { role: 'user' | 'assistant'; content: string }

const props = defineProps<{
  workflowId: number | null
}>()

const fabRef = ref<HTMLElement | null>(null)
const scrollRef = ref<HTMLElement | null>(null)
const drawerOpen = ref(false)
const logoOk = ref(true)
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
const chatMessages = ref<ChatMsg[]>([])
const draft = ref('')
const sending = ref(false)

const pos = reactive({ right: 24, bottom: 24 })
const storageKey = computed(() => {
  const id = props.workflowId != null ? String(props.workflowId) : 'draft'
  return `flowly_wf_guide_fab_pos_${id}`
})

const form = reactive({
  model_key: 'doubao-default',
})

let drag = false
let moved = false
let startX = 0
let startY = 0
let startRight = 0
let startBottom = 0
/** 拖拽结束后短时间内忽略双击，避免误开抽屉 */
let suppressOpenUntil = 0

function loadPos() {
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (!raw) return
    const j = JSON.parse(raw) as { right?: number; bottom?: number }
    if (typeof j.right === 'number' && Number.isFinite(j.right)) pos.right = Math.max(8, j.right)
    if (typeof j.bottom === 'number' && Number.isFinite(j.bottom)) pos.bottom = Math.max(8, j.bottom)
  } catch {
    /* ignore */
  }
}

function savePos() {
  try {
    localStorage.setItem(storageKey.value, JSON.stringify({ right: pos.right, bottom: pos.bottom }))
  } catch {
    /* ignore */
  }
}

function onFabPointerDown(e: PointerEvent) {
  if (e.button !== 0) return
  const el = fabRef.value
  if (!el) return
  drag = true
  moved = false
  startX = e.clientX
  startY = e.clientY
  startRight = pos.right
  startBottom = pos.bottom
  el.setPointerCapture(e.pointerId)

  const onMove = (ev: PointerEvent) => {
    if (!drag) return
    const dx = ev.clientX - startX
    const dy = ev.clientY - startY
    if (Math.abs(dx) + Math.abs(dy) > 4) moved = true
    pos.right = Math.max(8, startRight - dx)
    pos.bottom = Math.max(8, startBottom - dy)
  }
  const onUp = (ev: PointerEvent) => {
    drag = false
    try {
      el.releasePointerCapture(ev.pointerId)
    } catch {
      /* ignore */
    }
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    window.removeEventListener('pointercancel', onUp)
    if (moved) {
      savePos()
      suppressOpenUntil = Date.now() + 400
    }
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
  window.addEventListener('pointercancel', onUp)
}

async function ensureModels() {
  if (models.value.length) return
  try {
    const res = await api.get<{ models: CatalogModel[] }>('/ai/models')
    models.value = res.data.models ?? []
    if (!models.value.length) {
      ElMessage.warning('未获取到可用模型列表')
      return
    }
    if (!models.value.some((x) => x.key === form.model_key)) {
      form.model_key = models.value[0].key
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message ?? '获取模型列表失败')
  }
}

async function openDrawer() {
  if (Date.now() < suppressOpenUntil) return
  drawerOpen.value = true
  await ensureModels()
  if (!String(form.model_key || '').trim() && models.value[0]) {
    form.model_key = models.value[0].key
  }
  if (!chatMessages.value.length) {
    chatMessages.value.push({
      role: 'assistant',
      content:
        '我是工作流助手，可帮你梳理节点与连线、保存校验、画布运行与调试思路。可直接描述你的目标或报错信息。',
    })
  }
}

function onDraftKeydown(e: KeyboardEvent) {
  if (e.key !== 'Enter' || e.shiftKey) return
  e.preventDefault()
  send()
}

async function scrollToBottom() {
  await nextTick()
  const el = scrollRef.value
  if (el) el.scrollTop = el.scrollHeight
}

async function send() {
  const text = String(draft.value ?? '').trim()
  if (!text) {
    ElMessage.warning('请输入内容')
    return
  }
  if (!String(form.model_key || '').trim()) {
    ElMessage.warning('请选择 AI 模型')
    return
  }
  sending.value = true
  chatMessages.value.push({ role: 'user', content: text })
  draft.value = ''
  await scrollToBottom()
  try {
    const apiMessages = chatMessages.value.map((m) => ({ role: m.role, content: m.content }))
    const res = await api.post<{ reply: string; used_provider: string; used_model: string }>(
      '/ai/workflow-guide/chat',
      {
        messages: apiMessages,
        model_key: form.model_key,
        workflow_id: props.workflowId,
      }
    )
    const reply = String(res.data?.reply ?? '').trim() || '（空回复）'
    chatMessages.value.push({ role: 'assistant', content: reply })
    await scrollToBottom()
  } catch (e: any) {
    const msg = e?.response?.data?.message
    const detail =
      typeof msg === 'string'
        ? msg
        : msg && typeof msg === 'object' && 'message' in msg
          ? String((msg as { message?: string }).message)
          : e?.response?.data?.detail
    ElMessage.error(detail ?? '发送失败')
    chatMessages.value.pop()
    draft.value = text
  } finally {
    sending.value = false
  }
}

watch(
  () => props.workflowId,
  () => {
    loadPos()
  }
)

watch(drawerOpen, (v) => {
  if (v) void scrollToBottom()
})

onMounted(() => {
  loadPos()
})

onBeforeUnmount(() => {
  savePos()
})
</script>

<style scoped lang="scss">
.wf-guide-fab {
  position: fixed;
  z-index: 3000;
  width: 56px;
  height: 56px;
  cursor: grab;
  user-select: none;
  touch-action: none;
}

.wf-guide-fab:active {
  cursor: grabbing;
}

.fab-inner {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 50%;
  padding: 0;
  background: #ffffff;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
}

.fab-logo {
  width: 70%;
  height: 70%;
  object-fit: contain;
  pointer-events: none;
}

.fab-fallback {
  position: absolute;
  font-size: 20px;
  font-weight: 700;
  color: #409eff;
  pointer-events: none;
}

.drawer-body {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 320px;
  gap: 10px;
}

.model-row {
  display: flex;
  gap: 8px;
}

.m-title {
  font-size: 13px;
  font-weight: 600;
}

.m-sub {
  font-size: 11px;
  color: #888888;
  line-height: 1.3;
  white-space: normal;
}

.grow {
  flex: 1;
  min-width: 0;
}

.messages {
  flex: 1;
  overflow: auto;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 10px;
  background: #fafafa;
}

.bubble {
  margin-bottom: 12px;
}

.bubble .role {
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
}

.bubble .text {
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
}

.bubble.user .text {
  background: #ecf5ff;
  padding: 8px 10px;
  border-radius: 8px;
}

.bubble.assistant .text {
  background: #fff;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.composer {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
