<template>
  <div class="chat-page">
    <!-- Sidebar: session list -->
    <aside class="chat-sidebar">
      <div class="sidebar-header">
        <span class="sidebar-title">对话历史</span>
        <div class="sidebar-actions">
          <el-button size="small" text @click="startNewChat" title="新对话">
            <el-icon><Plus /></el-icon>
          </el-button>
          <el-button size="small" text @click="clearCurrentChat" title="清空当前对话">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>

      <div class="session-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: currentSessionId === session.id }"
          @click="loadSession(session.id)"
        >
          <el-icon class="session-icon"><ChatLineSquare /></el-icon>
          <span class="session-title">{{ session.title || '新对话' }}</span>
          <el-button
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

    <!-- Main chat area -->
    <main class="chat-main">
      <!-- Messages -->
      <div class="messages-area" ref="messagesAreaRef">
        <div v-if="messages.length === 0" class="empty-state">
          <el-icon class="empty-icon"><ChatDotRound /></el-icon>
          <h3>开始一个新对话</h3>
          <p>输入消息与 AI 开始交流，支持多轮对话和工具调用</p>
        </div>

        <div v-for="(msg, idx) in messages" :key="idx" class="message-wrapper" :class="msg.role">
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

        <!-- Streaming indicator -->
        <div v-if="streaming" class="message-wrapper assistant">
          <div class="message-avatar">
            <el-icon class="avatar-icon"><MagicStick /></el-icon>
          </div>
          <div class="message-bubble">
            <div class="message-content" v-html="renderMarkdown(streamingContent)"></div>
          </div>
        </div>
      </div>

      <!-- Input area -->
      <div class="chat-input-area">
        <div class="chat-input-wrapper">
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
            <span class="model-hint">
              模型: {{ auth.user?.ai_model || 'gpt-4o' }}
            </span>
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

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at?: string
}

interface Session {
  id: string
  title: string
  messages: ChatMessage[]
  lastQuery?: string
}

const auth = useAuthStore()
const messages = ref<ChatMessage[]>([])
const sessions = ref<Session[]>([])
const currentSessionId = ref<string | null>(null)
const inputText = ref('')
const streaming = ref(false)
const streamingContent = ref('')
const messagesAreaRef = ref<HTMLElement>()

let ws: WebSocket | null = null
let currentThreadId: string | null = null

function renderMarkdown(text: string): string {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Code blocks (```language\ncode\n```)
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, _lang, code) => {
    return `<pre class="code-block"><code>${code.trim()}</code></pre>`
  })

  // Inline code (`code`)
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')

  // Bold (**text**)
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')

  // Italic (*text*)
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')

  // Line breaks
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

function startNewChat() {
  const id = crypto.randomUUID()
  sessions.value.unshift({ id, title: '', messages: [] })
  currentSessionId.value = id
  messages.value = []
  currentThreadId = null
  scrollToBottom()
}

function loadSession(id: string) {
  const session = sessions.value.find((s) => s.id === id)
  if (!session) return
  currentSessionId.value = id
  messages.value = [...session.messages]
  currentThreadId = session.id !== currentSessionId.value ? session.id : currentThreadId
  scrollToBottom()
}

function deleteSession(id: string) {
  sessions.value = sessions.value.filter((s) => s.id !== id)
  if (currentSessionId.value === id) {
    startNewChat()
  }
}

function clearCurrentChat() {
  messages.value = []
  const session = sessions.value.find((s) => s.id === currentSessionId.value)
  if (session) session.messages = []
  scrollToBottom()
}

function saveSession() {
  const session = sessions.value.find((s) => s.id === currentSessionId.value)
  if (session) session.messages = [...messages.value]
}

function retryLast() {
  if (messages.value.length === 0) return
  // Find the last user message
  const userMsgIdx = messages.value.map(m => m.role).lastIndexOf('user')
  if (userMsgIdx === -1) return

  // Trim to user message
  const userMsg = messages.value[userMsgIdx]
  messages.value = messages.value.slice(0, userMsgIdx)
  inputText.value = userMsg.content
  sendMessage()
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || streaming.value) return

  const userMsg: ChatMessage = { role: 'user', content: text, created_at: new Date().toISOString() }
  messages.value.push(userMsg)
  inputText.value = ''
  scrollToBottom()

  const session = sessions.value.find((s) => s.id === currentSessionId.value)
  if (session) {
    session.messages = [...messages.value]
    if (!session.title && text) {
      session.title = text.slice(0, 30)
    }
    session.lastQuery = text
  }

  await streamResponse(text)
}

async function streamResponse(query: string) {
  streaming.value = true
  streamingContent.value = ''

  const threadId = currentThreadId || crypto.randomUUID()
  currentThreadId = threadId

  if (!sessions.value.find((s) => s.id === currentSessionId.value)) {
    const session: Session = {
      id: currentSessionId.value!,
      title: query.slice(0, 30),
      messages: [...messages.value],
      lastQuery: query,
    }
    sessions.value.unshift(session)
  }

  try {
    await api.post('/workflows/run', {
      query,
      context: {},
      workflow_id: null,
      thread_id: threadId,
    })

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/workflow/${threadId}/`
    ws = new WebSocket(wsUrl)

    let assistantContent = ''
    let resolved = false

    ws.onopen = () => { console.debug('[WS] Connected to thread', threadId) }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.event_type === 'connected') return

        if (data.event_type === 'token' && data.content) {
          assistantContent += data.content
          streamingContent.value = assistantContent
          scrollToBottom()
          return
        }

        if (data.event_type === 'message' && data.content) {
          assistantContent += data.content
          streamingContent.value = assistantContent
          scrollToBottom()
          return
        }

        if (data.event_type === 'workflow_end') {
          ws?.close()
          ws = null
          resolved = true
          streaming.value = false
          streamingContent.value = ''

          // Flush accumulated content
          if (assistantContent) {
            const lastMsg = messages.value[messages.value.length - 1]
            if (lastMsg?.role === 'user') {
              messages.value.push({ role: 'assistant', content: assistantContent, created_at: new Date().toISOString() })
            } else if (lastMsg?.role === 'assistant') {
              lastMsg.content = assistantContent
            }
          } else if (data.result?.response) {
            messages.value.push({ role: 'assistant', content: data.result.response, created_at: new Date().toISOString() })
          }
          saveSession()
          scrollToBottom()
          return
        }

        if (data.event_type === 'workflow_error') {
          ws?.close()
          ws = null
          resolved = true
          streaming.value = false
          streamingContent.value = ''
          messages.value.push({ role: 'assistant', content: `错误: ${data.error}`, created_at: new Date().toISOString() })
          saveSession()
          scrollToBottom()
          return
        }
      } catch {
        // ignore
      }
    }

    ws.onerror = () => {
      ws?.close()
      ws = null
      if (!resolved) {
        ElMessage.error('连接中断，请重试')
      }
      resolved = true
      streaming.value = false
      streamingContent.value = ''
    }

    ws.onclose = () => {
      if (!resolved) {
        resolved = true
        streaming.value = false
        streamingContent.value = ''
      }
    }

    setTimeout(() => {
      if (!resolved) {
        ws?.close()
        ws = null
        resolved = true
        streaming.value = false
        streamingContent.value = ''
        ElMessage.warning('响应超时')
      }
    }, 120000)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '发送失败，请检查后端连接')
    streaming.value = false
    streamingContent.value = ''
  }

  onUnmounted(() => {
    ws?.close()
    ws = null
  })
}

onMounted(() => {
  if (!currentSessionId.value) startNewChat()
  try {
    const saved = localStorage.getItem('flowly_chat_sessions')
    if (saved) sessions.value = JSON.parse(saved)
  } catch { /* ignore */ }
})

watch(sessions, (val) => {
  try {
    localStorage.setItem('flowly_chat_sessions', JSON.stringify(val.slice(0, 50)))
  } catch { /* ignore */ }
}, { deep: true })
</script>

<style scoped lang="scss">
.chat-page {
  display: flex;
  height: calc(100vh - 56px);
  overflow: hidden;
}

// ── Sidebar ──────────────────────────────────────────────────────────────────

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

// ── Chat Main ────────────────────────────────────────────────────────────────

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

// ── Input Area ──────────────────────────────────────────────────────────────

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
