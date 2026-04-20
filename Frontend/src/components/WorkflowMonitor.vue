<template>
  <div class="workflow-monitor">
    <!-- ── Chat Panel ──────────────────────────────────────────────── -->
    <el-card class="chat-card" shadow="never">
      <template #header>
        <div class="chat-header">
          <span>执行对话</span>
          <div class="chat-meta">
            <el-tag
              v-if="store.threadId"
              size="small"
              type="info"
              class="thread-tag"
              :title="`Thread: ${store.threadId}`"
            >
              {{ shortThreadId }}
            </el-tag>
            <el-tag
              :type="statusTagType"
              size="small"
              effect="plain"
            >
              {{ statusLabel }}
            </el-tag>
          </div>
        </div>
      </template>

      <!-- Message List -->
      <div ref="messagesEl" class="messages-container">
        <el-empty
          v-if="store.messages.length === 0 && !store.isRunning"
          description="暂无消息，运行工作流后将显示对话记录"
        />

        <div
          v-for="msg in store.messages"
          :key="msg.id"
          class="message-wrapper"
          :class="[`role-${msg.role}`]"
        >
          <div class="message-bubble">
            <div class="message-role-icon">
              <el-icon v-if="msg.role === 'user'"><User /></el-icon>
              <el-icon v-else-if="msg.role === 'assistant'"><ChatDotRound /></el-icon>
              <el-icon v-else-if="msg.role === 'tool'"><Operation /></el-icon>
              <el-icon v-else><InfoFilled /></el-icon>
            </div>
            <div class="message-content">
              <div class="message-text">{{ msg.content }}</div>
              <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
            </div>
          </div>
        </div>

        <!-- Streaming indicator -->
        <div v-if="store.isRunning && !store.streamingContent" class="message-wrapper role-assistant">
          <div class="message-bubble">
            <div class="message-role-icon">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <div class="message-content">
              <el-icon class="typing-indicator"><Loading /></el-icon>
            </div>
          </div>
        </div>

        <!-- Live token accumulation -->
        <div v-if="store.streamingContent" class="message-wrapper role-assistant streaming-bubble">
          <div class="message-bubble">
            <div class="message-role-icon">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <div class="message-content">
              <div class="message-text streaming-text">{{ store.streamingContent }}<span class="cursor-blink">|</span></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Pending Approval UI -->
      <div v-if="store.pendingApproval" class="approval-banner">
        <div class="approval-icon"><el-icon><QuestionFilled /></el-icon></div>
        <div class="approval-text">
          <strong>需要审批</strong>
          <p>{{ store.pendingQuestion }}</p>
        </div>
        <div class="approval-actions">
          <el-button size="small" @click="handleApprove">
            <el-icon><Check /></el-icon>
            批准
          </el-button>
          <el-button size="small" @click="handleReject">
            <el-icon><Close /></el-icon>
            拒绝
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- ── Node Status Sidebar ────────────────────────────────────── -->
    <el-card class="status-card" shadow="never">
      <template #header>
        <div class="status-header">
          <span>节点状态</span>
          <el-tooltip content="实时显示工作流节点执行进度">
            <el-icon><InfoFilled /></el-icon>
          </el-tooltip>
        </div>
      </template>

      <div v-if="store.nodeTimeline.length === 0" class="empty-nodes">
        <el-empty description="暂无活跃节点" :image-size="60" />
      </div>

      <el-timeline v-else class="node-timeline" :reverse="false">
        <el-timeline-item
          v-for="node in store.nodeTimeline"
          :key="node.node"
          :type="timelineItemType(node)"
          :hollow="node.status === 'idle'"
        >
          <template #dot>
            <div class="node-dot" :class="`status-${node.status}`">
              <el-icon v-if="node.status === 'running'"><Loading /></el-icon>
              <el-icon v-else-if="node.status === 'completed'"><Check /></el-icon>
              <el-icon v-else-if="node.status === 'failed'"><Close /></el-icon>
              <el-icon v-else><More /></el-icon>
            </div>
          </template>

          <div class="timeline-node">
            <div class="node-name">
              <el-icon v-if="isToolNode(node.node)"><Operation /></el-icon>
              <el-icon v-else><ChatLineSquare /></el-icon>
              {{ node.node }}
            </div>
            <div class="node-meta">
              <el-tag
                size="small"
                :type="nodeStatusTagType(node.status)"
                effect="plain"
              >
                {{ nodeStatusLabel(node.status) }}
              </el-tag>
              <span v-if="node.started_at" class="node-time">
                {{ formatTime(node.started_at) }}
              </span>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>

      <!-- Progress indicator -->
      <div v-if="store.isRunning" class="progress-section">
        <el-progress
          :percentage="executionProgress"
          :status="progressStatus"
          :indeterminate="store.nodeTimeline.every(n => n.status !== 'completed')"
          :stroke-width="6"
        />
        <span class="progress-label">工作流进度</span>
      </div>

      <!-- Completion summary -->
      <el-result
        v-if="store.isFinished"
        :icon="store.workflowStatus === 'completed' ? 'success' : 'error'"
        :title="store.workflowStatus === 'completed' ? '工作流已完成' : '工作流失败'"
        :sub-title="store.errorMessage ?? '执行结束'"
        class="completion-result"
      >
        <template #extra>
          <el-button size="small" @click="$emit('reset')">新运行</el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import {
  User,
  ChatDotRound,
  Operation,
  InfoFilled,
  QuestionFilled,
  Check,
  Close,
  Loading,
  More,
  ChatLineSquare,
} from '@element-plus/icons-vue'
import { useWorkflowStore } from '@/stores/workflow'
import type { WorkflowNodeState } from '@/types'

defineEmits<{
  reset: []
}>()

const store = useWorkflowStore()
const messagesEl = ref<HTMLElement | null>(null)

// ── Thread ID short display ─────────────────────────────────────────────────

const shortThreadId = computed(() => {
  const id = store.threadId ?? ''
  return id.length > 8 ? `${id.slice(0, 8)}…` : id
})

// ── Status ──────────────────────────────────────────────────────────────────

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: '等待',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
  }
  return map[store.workflowStatus] ?? store.workflowStatus
})

const statusTagType = computed(() => {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
  }
  return map[store.workflowStatus] ?? 'info'
})

// ── Timeline ─────────────────────────────────────────────────────────────────

function timelineItemType(node: WorkflowNodeState): string {
  const map: Record<string, string> = {
    completed: 'success',
    running: 'primary',
    failed: 'danger',
    idle: 'info',
  }
  return map[node.status] ?? 'info'
}

function nodeStatusTagType(status: string): string {
  const map: Record<string, string> = {
    completed: 'success',
    running: 'primary',
    failed: 'danger',
    idle: 'info',
  }
  return map[status] ?? 'info'
}

function isToolNode(name: string): boolean {
  return name.toLowerCase().includes('tool')
}

function nodeStatusLabel(status: string): string {
  const map: Record<string, string> = {
    completed: '已完成',
    running: '运行中',
    failed: '失败',
    idle: '空闲',
  }
  return map[status] ?? status
}

// ── Progress ─────────────────────────────────────────────────────────────────

const executionProgress = computed(() => {
  const nodes = store.nodeTimeline
  if (nodes.length === 0) return 0
  const completed = nodes.filter((n) => n.status === 'completed').length
  return Math.round((completed / nodes.length) * 100)
})

const progressStatus = computed(() => {
  if (store.workflowStatus === 'failed') return 'exception'
  if (store.workflowStatus === 'completed') return 'success'
  return undefined
})

// ── Auto-scroll chat ────────────────────────────────────────────────────────

watch(
  () => store.messages.length,
  () => {
    nextTick(() => {
      if (messagesEl.value) {
        messagesEl.value.scrollTop = messagesEl.value.scrollHeight
      }
    })
  }
)

// ── Time formatter ───────────────────────────────────────────────────────────

function formatTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// ── Approval handlers ────────────────────────────────────────────────────────

function handleApprove() {
  store.resumeWorkflow({ approved: true, resume_input: 'User approved' })
}

function handleReject() {
  store.resumeWorkflow({ approved: false, resume_input: 'User rejected' })
}
</script>

<style scoped lang="scss">
.workflow-monitor {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 16px;
  height: 100%;
  align-items: start;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}

// ── Chat Card ────────────────────────────────────────────────────────────────

.chat-card {
  border-radius: 4px;
  border: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  max-height: 70vh;

  :deep(.el-card__header) {
    padding: 12px 16px;
    border-bottom: 1px solid #f0f0f0;
  }

  :deep(.el-card__body) {
    padding: 0;
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 14px;
  color: #000000;

  .chat-meta {
    display: flex;
    align-items: center;
    gap: 8px;

    .thread-tag {
      font-family: monospace;
      font-size: 11px;
    }
  }
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 55vh;
  scroll-behavior: smooth;
}

.message-wrapper {
  display: flex;
  flex-direction: column;

  &.role-user {
    align-items: flex-end;

    .message-bubble {
      background: #000000;
      color: #ffffff;
      border-radius: 16px 16px 4px 16px;
      max-width: 80%;
    }
  }

  &.role-assistant {
    align-items: flex-start;

    .message-bubble {
      background: #f5f5f5;
      color: #000000;
      border-radius: 16px 16px 16px 4px;
      max-width: 80%;
    }
  }

  &.role-tool,
  &.role-system {
    align-items: flex-start;

    .message-bubble {
      background: #f0f0f0;
      color: #333333;
      border-radius: 16px 16px 16px 4px;
      max-width: 90%;
    }
  }
}

.message-bubble {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px;

  .message-role-icon {
    flex-shrink: 0;
    margin-top: 2px;
    color: #000000;
  }

  .message-content {
    flex: 1;
    min-width: 0;
  }

  .message-text {
    font-size: 14px;
    line-height: 1.6;
    color: inherit;
    word-break: break-word;
    white-space: pre-wrap;
  }

  .message-time {
    margin-top: 4px;
    font-size: 11px;
    color: #999999;
    text-align: right;
  }
}

.typing-indicator {
  animation: rotate 1s linear infinite;
  color: #666666;
  font-size: 18px;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.cursor-blink {
  animation: blink 1s step-end infinite;
  color: #000000;
  font-weight: bold;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.streaming-text {
  color: #000000;
}

// ── Approval Banner ─────────────────────────────────────────────────────────

.approval-banner {
  border-top: 1px solid #f0f0f0;
  padding: 12px 16px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: #f5f5f5;

  .approval-icon {
    color: #333333;
    font-size: 20px;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .approval-text {
    flex: 1;

    strong {
      display: block;
      margin-bottom: 4px;
      color: #000000;
    }

    p {
      margin: 0;
      font-size: 13px;
      color: #333333;
    }
  }

  .approval-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }
}

// ── Status Card ─────────────────────────────────────────────────────────────

.status-card {
  border-radius: 4px;
  border: 1px solid #e0e0e0;

  :deep(.el-card__header) {
    padding: 12px 16px;
    border-bottom: 1px solid #f0f0f0;
    font-weight: 600;
    font-size: 14px;
    color: #000000;
  }

  :deep(.el-card__body) {
    padding: 12px 16px;
  }
}

.status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.empty-nodes {
  padding: 16px 0;
}

.node-timeline {
  .node-dot {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;

    &.status-running {
      background: #e0e0e0;
      color: #000000;
      animation: pulse 1.5s ease-in-out infinite;
    }

    &.status-completed {
      background: #333333;
      color: #ffffff;
    }

    &.status-failed {
      background: #000000;
      color: #ffffff;
    }

    &.status-idle {
      background: #f5f5f5;
      color: #666666;
    }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.9); }
}

.timeline-node {
  .node-name {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    font-weight: 500;
    color: #000000;
    margin-bottom: 4px;
  }

  .node-meta {
    display: flex;
    align-items: center;
    gap: 8px;

    .node-time {
      font-size: 11px;
      color: #666666;
    }
  }
}

.progress-section {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;

  .progress-label {
    font-size: 12px;
    color: #666666;
    text-align: center;
  }
}

.completion-result {
  margin-top: 12px;

  :deep(.el-result__title) {
    font-size: 15px;
  }
}
</style>
