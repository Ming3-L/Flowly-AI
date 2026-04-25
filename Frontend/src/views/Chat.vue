<template>
  <div class="chat-page">
    <!-- 侧边栏：会话列表 -->
    <aside class="chat-sidebar">
      <div class="sidebar-header">
        <span class="sidebar-title">对话历史</span>
        <div class="sidebar-actions">
          <el-button size="small" text @click="startNewChat" title="新对话">
            <el-icon><Plus /></el-icon>
          </el-button>
          <el-button
            size="small"
            text
            @click="toggleSelectionMode"
            :title="selectionMode ? '退出选择' : '选择删除'"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>

      <div v-if="selectionMode" class="sidebar-batchbar">
        <span class="batch-tip">已选 {{ selectedCount }} 个</span>
        <div class="batch-actions">
          <el-button size="small" text @click="selectAllSessions">全选</el-button>
          <el-button size="small" text @click="clearSelectedSessions">清空</el-button>
          <el-button size="small" type="danger" @click="deleteSelectedSessions" :disabled="selectedCount === 0">
            删除
          </el-button>
        </div>
      </div>

      <div class="session-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: currentSessionId === session.id }"
          @click="onSessionRowClick(session.id)"
        >
          <el-checkbox
            v-if="selectionMode"
            class="session-check"
            :model-value="isSessionSelected(session.id)"
            @click.stop
            @change="() => toggleSessionSelected(session.id)"
          />
          <el-icon class="session-icon"><ChatLineSquare /></el-icon>
          <span class="session-title">{{ session.title || '新对话' }}</span>
          <el-button
            v-if="!selectionMode"
            size="small"
            text
            class="delete-btn"
            @click.stop="deleteSession(session.id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <div v-if="sessions.length === 0" class="no-sessions">
          暂无对话记录
        </div>
      </div>
    </aside>

    <!-- 主聊天区域 -->
    <main class="chat-main">
      <!-- 消息列表 -->
      <div class="messages-area" ref="messagesAreaRef">
        <div v-if="messages.length === 0" class="empty-state">
          <el-icon class="empty-icon"><ChatDotRound /></el-icon>
          <h3>开始一个新对话</h3>
          <p>输入消息与 AI 开始交流，支持多轮对话和工具调用</p>
        </div>

        <div v-for="(msg, idx) in messages" :key="msg.id ?? idx" class="message-wrapper" :class="msg.role">
          <div class="message-avatar">
            <el-icon v-if="msg.role === 'user'" class="avatar-icon"><UserFilled /></el-icon>
            <el-icon v-else class="avatar-icon"><MagicStick /></el-icon>
          </div>
          <div class="message-bubble">
            <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
            <div v-if="(msg.attachments || []).length" class="media-panel">
              <div v-for="(a, ai) in (msg.attachments || [])" :key="ai" class="media-item">
                <template v-if="attachmentKind(a) === 'image'">
                  <img class="media-preview-img" :src="attachmentPreviewUrl(a)" alt="image" />
                </template>
                <template v-else-if="attachmentKind(a) === 'audio'">
                  <audio class="media-preview-audio" :src="attachmentPreviewUrl(a)" controls />
                </template>
                <template v-else-if="attachmentKind(a) === 'video'">
                  <video class="media-preview-video" :src="attachmentPreviewUrl(a)" controls />
                </template>
                <template v-else>
                  <div class="media-file-row">
                    <span class="media-file-pill">{{ attachmentKind(a) }}</span>
                    <a class="media-link" :href="attachmentPreviewUrl(a)" target="_blank" rel="noopener noreferrer">
                      打开资源
                    </a>
                  </div>
                </template>

                <div class="media-links">
                  <a
                    v-if="attachmentPreviewUrl(a)"
                    class="media-link"
                    :href="attachmentPreviewUrl(a)"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    预览链接
                  </a>
                  <a
                    v-if="attachmentDownloadUrl(a)"
                    class="media-link"
                    :href="attachmentDownloadUrl(a)"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    下载地址
                  </a>
                </div>
              </div>
            </div>
            <div class="message-meta">
              <span class="message-time">{{ formatTime(msg.created_at) }}</span>
              <el-button
                v-if="msg.role === 'assistant' && idx === messages.length - 1"
                size="small"
                text
                class="retry-btn"
                @click="retryLast"
              >
                <el-icon><RefreshLeft /></el-icon>
                重试
              </el-button>
            </div>
          </div>
        </div>

        <!-- 流式输出提示 -->
        <div v-if="streaming" class="message-wrapper assistant">
          <div class="message-avatar">
            <el-icon class="avatar-icon"><MagicStick /></el-icon>
          </div>
          <div class="message-bubble">
            <div class="message-content" v-html="renderMarkdown(streamingContent)"></div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="chat-input-area">
        <div class="chat-input-wrapper">
          <div class="attach-row">
            <el-upload
              v-model:file-list="chatFileList"
              :auto-upload="false"
              :multiple="true"
              :limit="4"
              :disabled="streaming"
              accept="image/*,audio/*,video/*"
            >
              <el-button size="small" :disabled="streaming">选择附件</el-button>
            </el-upload>
            <span class="attach-tip">可选：图片/音频/视频（图片将参与多模态理解，其它作为链接附带）</span>
          </div>
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="3"
            placeholder="输入消息... (Shift+Enter 换行，Enter 发送)"
            resize="none"
            :disabled="streaming"
            @keydown.enter.exact.prevent="sendMessage"
            @keydown.enter.shift.exact="() => {}"
          />
          <div class="input-actions">
            <div class="model-hint">
              <span style="margin-right:8px">模型</span>
              <el-select
                v-model="selectedModelKey"
                size="small"
                filterable
                style="width: 260px"
                :disabled="streaming"
                placeholder="选择模型"
                popper-class="chat-model-catalog-popper"
                @change="() => { loadSavedTtsVoice() }"
              >
                <el-option-group
                  v-for="(grp, gidx) in modelOptionGroups"
                  :key="`chat-model-grp-${gidx}-${grp.label}`"
                  :label="grp.label"
                >
                  <el-option
                    v-for="m in grp.rows"
                    :key="`chat-model-${m.key}`"
                    :label="m.label"
                    :value="m.key"
                    :title="m.scope_summary || m.description || ''"
                  >
                    <div class="chat-model-opt-title">
                      <span class="chat-model-opt-title__name">{{ m.label }}</span>
                      <span class="chat-model-opt-title__right">
                        <span v-if="m.has_custom_credentials" class="chat-model-own-key">自有密钥</span>
                        <span class="chat-model-route">{{ m.route }}</span>
                      </span>
                    </div>
                    <div class="chat-model-opt-desc">
                      {{ m.scope_summary || m.description || '' }}
                    </div>
                    <div class="chat-model-opt-meta">{{ modelIoHint(m) }}</div>
                    <div v-if="m.scopes?.length" class="chat-model-opt-tags">
                      <span v-for="(t, ti) in m.scopes" :key="ti" class="chat-model-opt-tag">{{ t }}</span>
                    </div>
                  </el-option>
                </el-option-group>
              </el-select>
              <el-popover v-if="currentTtsVariants().length"
                placement="top"
                width="320"
                trigger="click"
                :disabled="streaming"
              >
                <template #reference>
                  <el-button
                    size="small"
                    style="margin-left: 10px"
                    :disabled="streaming"
                  >
                    二级选项 &gt;
                  </el-button>
                </template>
                <div style="display:flex; align-items:center; gap:10px">
                  <div style="font-size:12px; color: var(--app-text-2); white-space: nowrap">音色/能力</div>
                  <el-select
                    v-model="selectedTtsVoiceId"
                    size="small"
                    filterable
                    style="width: 230px"
                    :disabled="streaming"
                    placeholder="请选择"
                    @change="saveTtsVoice"
                  >
                    <el-option
                      v-for="v in currentTtsVariants()"
                      :key="v.id"
                      :label="v.label"
                      :value="v.id"
                    />
                  </el-select>
                </div>
                <div style="margin-top:10px; font-size:12px; color: var(--app-text-2)">
                  共 {{ currentTtsVariants().length }} 项（将随本模型保存）
                </div>
              </el-popover>
            </div>
            <div class="input-btns">
              <el-button
                type="default"
                size="small"
                @click="clearCurrentChat"
                :disabled="streaming || messages.length === 0"
              >
                <el-icon><Delete /></el-icon>
                清空
              </el-button>
              <el-button
                type="primary"
                size="small"
                :loading="streaming"
                :disabled="!inputText.trim() || streaming"
                @click="sendMessage"
              >
                <el-icon><Promotion /></el-icon>
                发送
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ChatLineSquare, Delete, Plus, ChatDotRound,
  UserFilled, MagicStick, Promotion, RefreshLeft,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/utils/api'
import type { UploadUserFile } from 'element-plus'

type ChatAttachmentRow = {
  kind?: string
  type?: string
  url?: string
  public_url?: string
  proxy_url?: string
  download_url?: string
}

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at?: string
  id?: number
  attachments?: ChatAttachmentRow[]
}

interface Session {
  id: number
  title: string
  messages: ChatMessage[]
}

const messages = ref<ChatMessage[]>([])
const sessions = ref<Session[]>([])
const currentSessionId = ref<number | null>(null)
const inputText = ref('')
const streaming = ref(false)
const streamingContent = ref('')
const messagesAreaRef = ref<HTMLElement>()

const selectionMode = ref(false)
const selectedSessionIds = ref<Set<number>>(new Set())
const selectedCount = ref(0)

let ws: WebSocket | null = null // 兼容旧实现（工作流流式）；当前聊天发送接口已不再使用 WebSocket
useAuthStore() // 确保认证状态管理初始化，用于 JWT 处理

type AiModelRow = {
  key: string
  label: string
  route: string
  modalities?: string[]
  api_kind?: string
  show_in_canvas_llm_nodes?: boolean
  source?: string
  description?: string
  category_label?: string
  category_order?: number
  scopes?: string[]
  scope_summary?: string
  has_custom_credentials?: boolean
  variants?: Array<{ id: string; label: string; voice_type: string }>
}

const availableModels = ref<AiModelRow[]>([])
const modelOptionGroups = ref<Array<{ label: string; order: number; rows: AiModelRow[] }>>([])
const selectedModelKey = ref<string>('')
const selectedTtsVoiceId = ref<string>('')
const chatFileList = ref<UploadUserFile[]>([])

function currentTtsVariants(): Array<{ id: string; label: string; voice_type: string }> {
  const cm = currentModel()
  // 不限制模型类型：只要后端返回了 variants 就允许用户选择（用于 TTS 音色 / 能力模式等二级选项）
  return Array.isArray(cm?.variants) ? (cm!.variants as any) : []
}

function loadSavedTtsVoice() {
  const k = effectiveChatModelKey()
  const v = localStorage.getItem(`flowly_chat_tts_voice:${k}`) || ''
  selectedTtsVoiceId.value = v.trim()
}

function saveTtsVoice() {
  const k = effectiveChatModelKey()
  localStorage.setItem(`flowly_chat_tts_voice:${k}`, (selectedTtsVoiceId.value || '').trim())
}

function modelIoHint(m: AiModelRow): string {
  const kind = String(m.api_kind || 'ark_chat').toLowerCase()
  const rawMods = Array.isArray(m.modalities) ? m.modalities : []
  const mods = rawMods.map((x) => String(x || '').toLowerCase()).filter(Boolean)
  const inputs = new Set<string>(mods.length ? mods : ['text'])

  let out = '文本'
  if (kind === 'ark_embedding') out = '向量/Embedding'
  else if (kind === 'ark_image_gen') out = '图片'
  else if (kind === 'ark_video_gen') out = '视频'
  else if (kind === 'openspeech') out = '音频'
  else if (kind === 'ark_3d_gen') out = '3D'

  const inLabel = Array.from(inputs)
    .map((x) => (x === 'text' ? '文本' : x === 'image' ? '图片' : x === 'audio' ? '音频' : x === 'video' ? '视频' : x))
    .join(' / ')
  return `输入：${inLabel || '文本'} → 输出：${out}`
}

function buildModelGroups(rows: AiModelRow[]) {
  const map = new Map<string, { label: string; order: number; rows: AiModelRow[] }>()
  for (const r of rows) {
    const label = String(r.category_label || '其它').trim() || '其它'
    const order = Number(r.category_order ?? 500) || 500
    if (!map.has(label)) map.set(label, { label, order, rows: [] })
    const g = map.get(label)!
    g.order = Math.min(g.order, order)
    g.rows.push(r)
  }
  const groups = Array.from(map.values())
  groups.sort((a, b) => (a.order - b.order) || a.label.localeCompare(b.label))
  for (const g of groups) g.rows.sort((a, b) => String(a.label).localeCompare(String(b.label)))
  modelOptionGroups.value = groups
}

function loadSavedModelKey() {
  const saved = localStorage.getItem('flowly_chat_model_key') || ''
  selectedModelKey.value = saved.trim()
}

function saveModelKey() {
  localStorage.setItem('flowly_chat_model_key', (selectedModelKey.value || '').trim())
}

async function fetchModelCatalog() {
  try {
    const { data } = await api.get<{ models: AiModelRow[] }>('/ai/models')
    const rows = Array.isArray(data?.models) ? data.models : []
    // 显示全部模型目录（含生图/生视频/语音等），由后端按 api_kind 分流处理
    availableModels.value = rows
    buildModelGroups(rows)
    loadSavedTtsVoice()
    if (!selectedModelKey.value) {
      // 默认优先“智能路由”（更贴近豆包体验）；若账号无权限会在后端映射到默认接入点
      const preferred =
        availableModels.value.find((m) => m.key === 'ark-doubao-smart-router')?.key ||
        availableModels.value.find((m) => m.key === 'doubao-default')?.key ||
        availableModels.value[0]?.key ||
        ''
      selectedModelKey.value = preferred
      saveModelKey()
    } else {
      // 若已保存但列表中不存在，回退到第一个可用项
      const ok = availableModels.value.some((m) => m.key === selectedModelKey.value)
      if (!ok) {
        selectedModelKey.value = availableModels.value[0]?.key || ''
        saveModelKey()
      }
    }
  } catch {
    availableModels.value = []
    modelOptionGroups.value = []
    if (!selectedModelKey.value) selectedModelKey.value = 'doubao-default'
  }
}

function renderMarkdown(text: string): string {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // 简单链接化（http(s) / 站内 /api/...）
  html = html.replace(
    /((https?:\/\/[^\s<]+)|((\/api)\/[^\s<]+))/g,
    (m) => `<a href="${m}" target="_blank" rel="noopener noreferrer">${m}</a>`
  )

  // 代码块（```语言标识\n代码\n```）
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, _lang, code) => {
    return `<pre class="code-block"><code>${code.trim()}</code></pre>`
  })

  // 行内代码（`code`）
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')

  // 粗体（**text**）
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')

  // 斜体（*text*）
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')

  // 换行
  html = html.replace(/\n/g, '<br>')

  return html
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesAreaRef.value) {
      messagesAreaRef.value.scrollTop = messagesAreaRef.value.scrollHeight
    }
  })
}

function formatTime(iso?: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function attachmentKind(a: ChatAttachmentRow): string {
  const k = String(a.kind || a.type || '').trim().toLowerCase()
  if (k) return k
  const u = attachmentPreviewUrl(a)
  const low = String(u || '').toLowerCase()
  if (/\.(png|jpg|jpeg|gif|webp)(\?|$)/.test(low)) return 'image'
  if (/\.(mp3|wav|aac|flac|opus)(\?|$)/.test(low)) return 'audio'
  if (/\.(mp4|webm|mov)(\?|$)/.test(low)) return 'video'
  return 'file'
}

function attachmentPreviewUrl(a: ChatAttachmentRow): string {
  // 注意：<img>/<audio>/<video> 等标签无法自动携带 Authorization Header，
  // 因此 proxy_url（需 JWT）会导致 401，表现为图片不显示/音频 0 秒/视频无法播放。
  // 预览优先使用 public_url（带签名 token），其次才回退到其它字段。
  return String(a.public_url || a.url || a.download_url || a.proxy_url || '').trim()
}

function attachmentDownloadUrl(a: ChatAttachmentRow): string {
  const dl = String(a.download_url || '').trim()
  if (dl) return dl

  // 兼容旧消息：download_url 可能是需要 JWT 的 /api/media/proxy?...
  // 对于 public_url(/api/media/public?token=...)，前端可直接拼 download=1 实现免登录下载。
  const pub = String(a.public_url || '').trim()
  if (pub) {
    const sep = pub.includes('?') ? '&' : '?'
    return `${pub}${sep}download=1`
  }

  return String(a.proxy_url || '').trim()
}

async function fetchSessionList() {
  try {
    const { data } = await api.get<{ sessions: { id: number; topic: string; message_count: number }[] }>(
      '/chat/sessions'
    )
    sessions.value = (data.sessions || []).map((s) => ({
      id: s.id,
      title: s.topic || '新对话',
      messages: [],
    }))
  } catch {
    sessions.value = []
  }
}

async function fetchMessagesForSession(sessionId: number) {
  const { data } = await api.get<{ messages: { id: number; role: string; content: string; created_at: string; attachments?: any[] }[] }>(
    `/chat/sessions/${sessionId}/messages`
  )
  return (data.messages || []).map((m) => ({
    id: m.id,
    role: m.role as ChatMessage['role'],
    content: m.content || '',
    created_at: m.created_at,
    attachments: Array.isArray((m as any).attachments) ? (m as any).attachments : [],
  }))
}

async function startNewChat() {
  try {
    const { data } = await api.post<{ id: number; topic: string }>('/chat/sessions', { topic: '' })
    const row = data as { id: number; topic: string }
    sessions.value.unshift({ id: row.id, title: row.topic || '新对话', messages: [] })
    currentSessionId.value = row.id
    messages.value = []
    scrollToBottom()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '创建会话失败')
  }
}

async function loadSession(id: number) {
  const session = sessions.value.find((s) => s.id === id)
  if (!session) return
  currentSessionId.value = id
  try {
    messages.value = await fetchMessagesForSession(id)
    session.messages = [...messages.value]
  } catch {
    messages.value = []
  }
  scrollToBottom()
}

async function deleteSession(id: number) {
  try {
    await api.delete(`/chat/sessions/${id}`)
  } catch {
    /* 仍从列表移除，避免卡住 */
  }
  sessions.value = sessions.value.filter((s) => s.id !== id)
  if (currentSessionId.value === id) {
    currentSessionId.value = null
    messages.value = []
    if (sessions.value.length) await loadSession(sessions.value[0].id)
    else await startNewChat()
  }
}

async function clearCurrentChat() {
  const sid = currentSessionId.value
  if (sid == null) return
  try {
    await api.post(`/chat/sessions/${sid}/clear`)
    messages.value = []
    const session = sessions.value.find((s) => s.id === sid)
    if (session) session.messages = []
    scrollToBottom()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '清空失败')
  }
}

function syncSidebarTitleFromMessages() {
  const sid = currentSessionId.value
  if (sid == null) return
  const session = sessions.value.find((s) => s.id === sid)
  if (!session) return
  session.messages = [...messages.value]
  const firstUser = messages.value.find((m) => m.role === 'user')
  if (firstUser?.content && (!session.title || session.title === '新对话')) {
    session.title = firstUser.content.slice(0, 30)
  }
}

function retryLast() {
  if (messages.value.length === 0) return
  // 找到最后一条用户消息
  const userMsgIdx = messages.value.map(m => m.role).lastIndexOf('user')
  if (userMsgIdx === -1) return

  // 回退到该条用户消息之前，并将其内容放回输入框
  const userMsg = messages.value[userMsgIdx]
  messages.value = messages.value.slice(0, userMsgIdx)
  inputText.value = userMsg.content
  sendMessage()
}

async function ensureChatSession(): Promise<number | null> {
  if (currentSessionId.value != null) return currentSessionId.value
  try {
    const { data } = await api.post<{ id: number; topic: string }>('/chat/sessions', { topic: '' })
    const row = data as { id: number; topic: string }
    sessions.value.unshift({ id: row.id, title: row.topic || '新对话', messages: [] })
    currentSessionId.value = row.id
    return row.id
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '创建会话失败')
    return null
  }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || streaming.value) return

  const sid = await ensureChatSession()
  if (sid == null) return

  const userMsg: ChatMessage = { role: 'user', content: text, created_at: new Date().toISOString() }
  messages.value.push(userMsg)
  inputText.value = ''
  scrollToBottom()
  syncSidebarTitleFromMessages()

  await streamResponse(text, sid)
}

function effectiveChatModelKey(): string {
  const raw = (selectedModelKey.value || '').trim()
  return raw || 'doubao-default'
}

function currentModel(): AiModelRow | null {
  const key = effectiveChatModelKey()
  return availableModels.value.find((m) => m.key === key) ?? null
}

async function streamResponse(query: string, sessionId: number) {
  streaming.value = true
  streamingContent.value = ''

  try {
    const cm = currentModel()
    const mods = new Set((cm?.modalities ?? []).map((x) => String(x).toLowerCase()))
    const allowImageMm = (cm?.api_kind ?? 'ark_chat') === 'ark_chat' && mods.has('image')

    // 先上传附件（得到 public_url 供多模态模型抓取）
    const attachments: Array<{ type: string; url: string }> = []
    for (const f of chatFileList.value) {
      const raw = f.raw as File | undefined
      if (!raw) continue
      const fd = new FormData()
      fd.append('file', raw)
      const res = await api.post('/media/upload', fd, {
        timeout: 120000,
      })
      const mime = String(res.data?.mime || raw.type || '').toLowerCase()
      const url = String(res.data?.public_url || res.data?.proxy_url || '')
      const kind =
        mime.startsWith('image/') ? 'image' :
        mime.startsWith('audio/') ? 'audio' :
        mime.startsWith('video/') ? 'video' : 'file'
      if (!url) continue
      // 若当前对话模型不支持图像多模态，图片降级为普通附件链接，避免 400 InvalidParameter
      if (kind === 'image' && !allowImageMm) {
        attachments.push({ type: 'file', url })
      } else {
        attachments.push({ type: kind, url })
      }
    }

    const { data } = await api.post<{ ok: boolean; assistant_message?: ChatMessage; error?: string }>(
      `/chat/sessions/${sessionId}/send`,
      {
        content: query,
        model_key: effectiveChatModelKey(),
        tts_voice_type: (() => {
          const vs = currentTtsVariants()
          if (!vs.length) return ''
          const id = (selectedTtsVoiceId.value || '').trim()
          const found = vs.find((x) => x.id === id) || vs[0]
          return String(found?.voice_type || '').trim()
        })(),
        attachments,
      }
    )

    streaming.value = false
    streamingContent.value = ''
    chatFileList.value = []

    if (!data?.ok) {
      messages.value.push({
        role: 'assistant',
        content: `错误: ${data?.error || 'unknown_error'}`,
        created_at: new Date().toISOString(),
      })
      scrollToBottom()
      return
    }

    // 拉取全量消息，保持与后端一致（含时间/id）
    try {
      messages.value = await fetchMessagesForSession(sessionId)
      syncSidebarTitleFromMessages()
    } catch {
      if (data?.assistant_message?.content) {
        messages.value.push({
          role: 'assistant',
          content: data.assistant_message.content,
          created_at: data.assistant_message.created_at || new Date().toISOString(),
        })
      } else {
        messages.value.push({
          role: 'assistant',
          content: '（无返回）',
          created_at: new Date().toISOString(),
        })
      }
    }
    scrollToBottom()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '发送失败，请检查后端连接')
    streaming.value = false
    streamingContent.value = ''
    if (messages.value.length && messages.value[messages.value.length - 1]?.role === 'user') {
      messages.value.pop()
    }
  }
}

function toggleSelectionMode() {
  selectionMode.value = !selectionMode.value
  if (!selectionMode.value) {
    selectedSessionIds.value = new Set()
    selectedCount.value = 0
  }
}

function isSessionSelected(id: number) {
  return selectedSessionIds.value.has(id)
}

function toggleSessionSelected(id: number) {
  const s = new Set(selectedSessionIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedSessionIds.value = s
  selectedCount.value = s.size
}

function selectAllSessions() {
  const s = new Set<number>()
  for (const row of sessions.value) s.add(row.id)
  selectedSessionIds.value = s
  selectedCount.value = s.size
}

function clearSelectedSessions() {
  selectedSessionIds.value = new Set()
  selectedCount.value = 0
}

async function deleteSelectedSessions() {
  const ids = Array.from(selectedSessionIds.value)
  if (ids.length === 0) return
  try {
    await Promise.all(ids.map((id) => api.delete(`/chat/sessions/${id}`).catch(() => null)))
  } finally {
    // 刷新列表与当前会话
    await fetchSessionList()
    const still = sessions.value.find((s) => s.id === currentSessionId.value) != null
    if (!still) {
      currentSessionId.value = null
      messages.value = []
      if (sessions.value.length) await loadSession(sessions.value[0].id)
      else await startNewChat()
    }
    clearSelectedSessions()
    selectionMode.value = false
  }
}

function onSessionRowClick(id: number) {
  if (selectionMode.value) {
    toggleSessionSelected(id)
    return
  }
  loadSession(id)
}

onMounted(async () => {
  loadSavedModelKey()
  await fetchModelCatalog()
  await fetchSessionList()
  if (sessions.value.length) await loadSession(sessions.value[0].id)
  else await startNewChat()
})

watch(selectedModelKey, () => saveModelKey())

onUnmounted(() => {
  ws?.close()
  ws = null
})
</script>

<style scoped lang="scss">
.chat-page {
  display: flex;
  height: calc(100vh - 56px);
  overflow: hidden;
}

// ── 侧边栏 ──────────────────────────────────────────────────────────────────

.chat-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: var(--app-surface);
  border-right: 1px solid var(--app-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--app-border);
}

.sidebar-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--app-text);
}

.sidebar-actions {
  display: flex;
  gap: 4px;
}

.sidebar-batchbar {
  padding: 8px 12px;
  border-bottom: 1px solid var(--app-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--app-text-3);
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.session-check {
  flex-shrink: 0;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 2px;
  font-size: 13px;
  color: var(--app-text);
  transition: background 0.15s;

  &:hover {
    background: var(--el-fill-color-light);
    .delete-btn { opacity: 1; }
  }

  &.active {
    background: var(--app-surface);
    color: var(--app-text);
    font-weight: 500;

    .el-icon svg path {
      fill: var(--app-text) !important;
    }
    .session-icon {
      color: var(--app-text) !important;
    }
  }
}

.session-icon {
  font-size: 16px;
  flex-shrink: 0;
  color: var(--app-text-3);
}

.session-item.active .delete-btn {
  :deep(.el-icon) {
    color: var(--app-text) !important;
  }
  :deep(.el-icon svg path) {
    fill: var(--app-text) !important;
  }
}

.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-btn {
  opacity: 0;
  transition: opacity 0.15s;
  flex-shrink: 0;
}

.no-sessions {
  padding: 20px;
  text-align: center;
  font-size: 13px;
  color: var(--app-text-3);
}

// ── 聊天主区域 ────────────────────────────────────────────────────────────────

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--app-bg);
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--app-text-2);
  text-align: center;

  .empty-icon {
    font-size: 64px;
    margin-bottom: 16px;
    color: var(--app-text-3);
  }

  h3 { margin: 0 0 8px; font-weight: 600; color: var(--app-text); }
  p { margin: 0; font-size: 14px; color: var(--app-text-2); }
}

.message-wrapper {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;

  &.user { flex-direction: row-reverse; }

  .message-bubble {
    max-width: 70%;
    padding: 12px 16px;
    border-radius: 4px;
    font-size: 14px;
    line-height: 1.6;
  }

  &.user .message-bubble {
    background: var(--app-text);
    color: var(--app-surface);
    border-bottom-right-radius: 4px;
  }

  &.assistant .message-bubble {
    background: var(--app-surface);
    color: var(--app-text);
    border-bottom-left-radius: 4px;
  }
}

.message-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--el-fill-color);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-icon {
  font-size: 18px;
  color: var(--app-text-2);
}

.user .avatar-icon {
  color: var(--app-text);
}

.message-content {
  :deep(.code-block) {
    background: var(--app-surface-2);
    color: var(--app-text);
    padding: 12px;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 13px;
    font-family: 'Monaco', 'Menlo', monospace;
    margin: 8px 0;
    line-height: 1.5;
  }

  :deep(.inline-code) {
    background: var(--el-fill-color-light);
    color: var(--app-accent-danger);
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 13px;
    font-family: 'Monaco', 'Menlo', monospace;
  }
}

.user .message-content {
  :deep(.code-block) {
    background: var(--app-text);
    color: var(--app-surface);
  }
}

.message-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.message-time {
  font-size: 11px;
  color: var(--app-text-3);
  opacity: 0.7;
}

.retry-btn {
  font-size: 11px;
  padding: 0 4px;
  opacity: 0;
  transition: opacity 0.15s;
}

.message-wrapper:hover .retry-btn {
  opacity: 1;
}

// ── 输入区 ──────────────────────────────────────────────────────────────

.chat-input-area {
  padding: 12px 20px;
  background: var(--app-surface);
  border-top: 1px solid var(--app-border);
  flex-shrink: 0;
}

.chat-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.attach-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.attach-tip {
  font-size: 12px;
  color: var(--app-text-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.model-hint {
  font-size: 12px;
  color: var(--app-text-2);
}

.media-panel {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--app-border);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.media-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.media-preview-img {
  max-width: min(520px, 78vw);
  border-radius: 10px;
  border: 1px solid var(--app-border);
  background: var(--app-surface);
}

.media-preview-audio {
  width: min(520px, 78vw);
}

.media-preview-video {
  width: min(520px, 78vw);
  border-radius: 10px;
  border: 1px solid var(--app-border);
  background: var(--app-surface);
}

.media-links {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.media-link {
  font-size: 12px;
  color: var(--el-color-primary);
  text-decoration: none;
}
.media-link:hover {
  text-decoration: underline;
}

.media-file-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.media-file-pill {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.08);
  color: var(--app-text-2);
}

.input-btns {
  display: flex;
  gap: 8px;
}
</style>

<style>
/* 深色主题下激活会话项：背景深色，文字/图标白色 */
html.theme-dark .session-item.active {
  background: var(--app-surface);
  color: var(--app-text);
}
html.theme-dark .session-item.active .el-icon svg path {
  fill: var(--app-text) !important;
}
html.theme-dark .session-item.active .el-icon {
  color: var(--app-text) !important;
}
html.theme-dark .session-item.active .delete-btn .el-icon {
  color: var(--app-text) !important;
}
html.theme-dark .session-item.active .delete-btn .el-icon svg path {
  fill: var(--app-text) !important;
}
</style>

<style lang="scss">
/* 模型下拉 teleport 到 body，scoped 无法命中；加宽选项避免信息被挤压 */
.chat-model-catalog-popper {
  min-width: 320px !important;
  max-width: min(560px, 94vw);
}

.chat-model-catalog-popper .el-select-dropdown__item {
  height: auto !important;
  min-height: 44px;
  line-height: 1.45 !important;
  padding-top: 8px;
  padding-bottom: 8px;
  white-space: normal !important;
}

.chat-model-opt-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.chat-model-opt-title__name {
  font-weight: 600;
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-model-opt-title__right {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.chat-model-route {
  font-size: 11px;
  color: #999;
}

.chat-model-own-key {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 999px;
  border: 1px solid rgba(230, 162, 60, 0.55);
  color: #b88230;
}

.chat-model-opt-desc {
  margin-top: 4px;
  font-size: 12px;
  color: #666;
}

.chat-model-opt-meta {
  margin-top: 2px;
  font-size: 12px;
  color: #8c8c8c;
}

.chat-model-opt-tags {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chat-model-opt-tag {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 999px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  color: #444;
  background: rgba(0, 0, 0, 0.02);
}
</style>
