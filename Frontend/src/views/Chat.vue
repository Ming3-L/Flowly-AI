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
              >
                <el-option
                  v-for="m in availableModels"
                  :key="m.key"
                  :label="m.label"
                  :value="m.key"
                >
                  <span style="display:flex;align-items:center;justify-content:space-between;gap:8px">
                    <span style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                      {{ m.label }}
                    </span>
                    <span style="font-size:11px;color:#999">{{ m.route }}</span>
                  </span>
                </el-option>
              </el-select>
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

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at?: string
  id?: number
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
}

const availableModels = ref<AiModelRow[]>([])
const selectedModelKey = ref<string>('')
const chatFileList = ref<UploadUserFile[]>([])

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
  const { data } = await api.get<{ messages: { id: number; role: string; content: string; created_at: string }[] }>(
    `/chat/sessions/${sessionId}/messages`
  )
  return (data.messages || []).map((m) => ({
    id: m.id,
    role: m.role as ChatMessage['role'],
    content: m.content || '',
    created_at: m.created_at,
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
        headers: { 'Content-Type': 'multipart/form-data' },
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
  background: #fafafa;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e0e0e0;
}

.sidebar-title {
  font-weight: 600;
  font-size: 13px;
  color: #333333;
}

.sidebar-actions {
  display: flex;
  gap: 4px;
}

.sidebar-batchbar {
  padding: 8px 12px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: #666666;
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
  color: #333333;
  transition: background 0.15s;

  &:hover {
    background: #f0f0f0;
    .delete-btn { opacity: 1; }
  }

  &.active {
    background: #000000;
    color: #ffffff;
    font-weight: 500;
  }
}

.session-icon {
  font-size: 16px;
  flex-shrink: 0;
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
  color: #999999;
}

// ── 聊天主区域 ────────────────────────────────────────────────────────────────

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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
  color: #666666;
  text-align: center;

  .empty-icon {
    font-size: 64px;
    margin-bottom: 16px;
    color: #cccccc;
  }

  h3 { margin: 0 0 8px; font-weight: 600; color: #000000; }
  p { margin: 0; font-size: 14px; color: #666666; }
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
    background: #000000;
    color: #ffffff;
    border-bottom-right-radius: 4px;
  }

  &.assistant .message-bubble {
    background: #f5f5f5;
    color: #000000;
    border-bottom-left-radius: 4px;
  }
}

.message-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-icon {
  font-size: 18px;
  color: #333333;
}

.user .avatar-icon {
  color: #ffffff;
}

.message-content {
  :deep(.code-block) {
    background: #1a1a1a;
    color: #f8f8f2;
    padding: 12px;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 13px;
    font-family: 'Monaco', 'Menlo', monospace;
    margin: 8px 0;
    line-height: 1.5;
  }

  :deep(.inline-code) {
    background: rgba(0,0,0,0.08);
    color: #c7254e;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 13px;
    font-family: 'Monaco', 'Menlo', monospace;
  }
}

.user .message-content {
  :deep(.code-block) {
    background: #2a2a2a;
    color: #f8f8f2;
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
  color: #999999;
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
  background: #ffffff;
  border-top: 1px solid #e0e0e0;
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
  color: #888;
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
  color: #666666;
}

.input-btns {
  display: flex;
  gap: 8px;
}
</style>
