<template>
  <div class="workflow-monitor">
    <!-- ── Chat Panel ──────────────────────────────────────────────── -->
    <el-card class="chat-card" shadow="never">
      <template #header>
        <div class="chat-header">
          <span>{{ ui.t('wf.monitor.chatTitle') }}</span>
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
          :description="ui.t('wf.monitor.emptyMessages')"
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
          <strong>{{ ui.t('wf.monitor.approvalTitle') }}</strong>
          <p>{{ store.pendingQuestion }}</p>
        </div>
        <div class="approval-actions">
          <el-button size="small" @click="handleApprove">
            <el-icon><Check /></el-icon>
            {{ ui.t('wf.monitor.approve') }}
          </el-button>
          <el-button size="small" @click="handleReject">
            <el-icon><Close /></el-icon>
            {{ ui.t('wf.monitor.reject') }}
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- ── Node Status Sidebar ────────────────────────────────────── -->
    <el-card class="status-card" shadow="never">
      <template #header>
        <div class="status-header">
          <span>{{ ui.t('wf.monitor.statusPanelTitle') }}</span>
          <el-tooltip :content="ui.t('wf.monitor.statusPanelTooltip')">
            <el-icon><InfoFilled /></el-icon>
          </el-tooltip>
        </div>
      </template>

      <div v-if="store.nodeTimeline.length === 0" class="empty-nodes">
        <el-empty :description="ui.t('wf.monitor.emptyNodes')" :image-size="60" />
      </div>

      <el-timeline v-else class="node-timeline" :reverse="false">
        <el-timeline-item
          v-for="(node, idx) in store.nodeTimeline"
          :key="`${node.node}-${idx}-${node.status}`"
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
              {{ node.title || node.node }}
            </div>
            <div v-if="node.activity" class="node-activity">
              {{ node.activity }}
            </div>
            <div v-if="node.model_route" class="node-model-route">
              {{ ui.t('wf.monitor.nodeModelPrefix') }}{{ node.model_route }}
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
        <span class="progress-label">{{ ui.t('wf.monitor.progressLabel') }}</span>
      </div>

      <!-- Completion summary -->
      <el-result
        v-if="store.isFinished"
        :icon="store.workflowStatus === 'completed' ? 'success' : 'error'"
        :title="store.workflowStatus === 'completed' ? ui.t('wf.monitor.resultSuccessTitle') : ui.t('wf.monitor.resultFailTitle')"
        :sub-title="store.errorMessage ?? ui.t('wf.monitor.resultSubtitleDefault')"
        class="completion-result"
      >
        <template #extra>
          <el-button size="small" @click="$emit('reset')">{{ ui.t('wf.monitor.newRunAgain') }}</el-button>
        </template>
      </el-result>

      <!-- 完成后：正文 / 媒体预览与导出（依赖 executionId + GET /executions/...） -->
      <div
        v-if="store.isFinished && store.workflowStatus === 'completed' && store.executionId"
        class="export-panel"
      >
        <div class="export-panel-title">结果预览与导出</div>
        <el-alert v-if="artifactsError" type="warning" :closable="false" class="export-alert" :title="artifactsError" />
        <el-tabs v-model="previewTab" type="border-card" class="preview-tabs" @tab-change="onPreviewTabChange">
          <el-tab-pane label="文章" name="article">
            <div class="export-actions">
              <el-button size="small" @click="downloadArticle('txt')">下载 TXT</el-button>
              <el-button size="small" @click="downloadArticle('docx')">下载 Word</el-button>
            </div>
            <el-input
              type="textarea"
              :rows="8"
              readonly
              :model-value="artifacts?.article_text ?? ''"
              placeholder="暂无合并正文"
            />
          </el-tab-pane>
          <el-tab-pane label="图片" name="image">
            <div class="export-actions">
              <el-button size="small" :disabled="!hasImageUrls" @click="downloadImageFromUrl('png')">下载 PNG</el-button>
              <el-button size="small" :disabled="!hasImageUrls" @click="downloadImageFromUrl('jpeg')">下载 JPG</el-button>
              <el-button size="small" :disabled="!hasImageUrls" @click="downloadImageFromUrl('webp')">下载 WebP</el-button>
              <el-button size="small" type="primary" :loading="genImageLoading" @click="downloadAiImage('png')">
                AI 文生图 PNG
              </el-button>
              <el-button size="small" type="primary" :loading="genImageLoading" @click="downloadAiImage('jpeg')">
                AI 文生图 JPG
              </el-button>
            </div>
            <div v-if="previewImageUrl" class="preview-media">
              <img :src="previewImageUrl" alt="preview" />
            </div>
            <el-empty v-else description="无结果内图片 URL 时可直接文生图；有 URL 时切换到此页将尝试预览" />
          </el-tab-pane>
          <el-tab-pane label="音频" name="audio">
            <div class="export-actions">
              <el-button size="small" type="primary" :loading="ttsLoading" @click="downloadTts('mp3')">AI 朗读 MP3</el-button>
              <el-button size="small" type="primary" :loading="ttsLoading" @click="downloadTts('wav')">AI 朗读 WAV</el-button>
              <el-button size="small" :disabled="!hasAudioUrls" @click="downloadProxyMedia('audio')">下载结果内音频</el-button>
            </div>
            <audio v-if="previewAudioUrl" class="preview-audio" controls :src="previewAudioUrl" />
            <el-empty v-else description="可用 TTS 生成；若节点产出音频 URL 可预览与下载" />
          </el-tab-pane>
          <el-tab-pane label="视频" name="video">
            <div class="export-actions">
              <el-button size="small" :disabled="!hasVideoUrls" @click="downloadProxyMedia('video')">下载结果内视频</el-button>
            </div>
            <video v-if="previewVideoUrl" class="preview-video" controls :src="previewVideoUrl" />
            <el-empty v-else description="需在节点产出可访问的 video_url 后预览；AI 生成视频需另行接入厂商 API" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'
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
import { useUiLabelsStore } from '@/stores/uiLabels'
import type { WorkflowNodeState } from '@/types'

defineEmits<{
  reset: []
}>()

const store = useWorkflowStore()
const ui = useUiLabelsStore()
const messagesEl = ref<HTMLElement | null>(null)

// ── Thread ID short display ─────────────────────────────────────────────────

const shortThreadId = computed(() => {
  const id = store.threadId ?? ''
  return id.length > 8 ? `${id.slice(0, 8)}…` : id
})

// ── Status ──────────────────────────────────────────────────────────────────

const statusLabel = computed(() => {
  const s = store.workflowStatus
  if (s === 'pending') return ui.t('wf.monitor.status.pending')
  if (s === 'running') return ui.t('wf.monitor.status.running')
  if (s === 'completed') return ui.t('wf.monitor.status.completed')
  if (s === 'failed') return ui.t('wf.monitor.status.failed')
  return s
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
  if (status === 'completed') return ui.t('wf.node.status.completed')
  if (status === 'running') return ui.t('wf.node.status.running')
  if (status === 'failed') return ui.t('wf.node.status.failed')
  if (status === 'idle') return ui.t('wf.node.status.idle')
  return status
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

// ── 执行结果：预览与导出 ─────────────────────────────────────────────────────

interface MediaItem {
  node_id: string
  url: string
  field: string
}

interface ArtifactsResp {
  execution_id: number
  status: string
  has_canvas_outputs: boolean
  article_text: string
  media: { images: MediaItem[]; audios: MediaItem[]; videos: MediaItem[] }
}

const artifacts = ref<ArtifactsResp | null>(null)
const artifactsError = ref('')
const previewTab = ref('article')
const previewImageUrl = ref('')
const previewAudioUrl = ref('')
const previewVideoUrl = ref('')
const genImageLoading = ref(false)
const ttsLoading = ref(false)
const blobRegistry: string[] = []

function revokePreviewBlobs() {
  blobRegistry.forEach((u) => URL.revokeObjectURL(u))
  blobRegistry.length = 0
  previewImageUrl.value = ''
  previewAudioUrl.value = ''
  previewVideoUrl.value = ''
}

const hasImageUrls = computed(() => (artifacts.value?.media?.images?.length ?? 0) > 0)
const hasAudioUrls = computed(() => (artifacts.value?.media?.audios?.length ?? 0) > 0)
const hasVideoUrls = computed(() => (artifacts.value?.media?.videos?.length ?? 0) > 0)

watch(
  () =>
    [store.executionId, store.isFinished, store.workflowStatus] as [
      number | null,
      boolean,
      string,
    ],
  async ([id, fin, st]) => {
    revokePreviewBlobs()
    artifacts.value = null
    artifactsError.value = ''
    previewTab.value = 'article'
    if (!id || !fin || st !== 'completed') return
    try {
      const res = await api.get<ArtifactsResp>(`/executions/${id}/artifacts`)
      artifacts.value = res.data
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { message?: string } } }
      artifactsError.value = ax.response?.data?.message ?? '无法加载执行结果'
    }
  },
  { immediate: true }
)

watch(artifacts, async (a) => {
  if (!a || !store.executionId) return
  await onPreviewTabChange(previewTab.value)
})

async function onPreviewTabChange(name: string | number) {
  const tab = String(name)
  const id = store.executionId
  if (!id || !artifacts.value) return
  revokePreviewBlobs()
  if (tab === 'article') return
  try {
    if (tab === 'image' && hasImageUrls.value) {
      const u = artifacts.value.media.images[0].url
      const res = await api.get(`/executions/${id}/export/proxy`, {
        params: { url: u },
        responseType: 'blob',
        timeout: 120000,
      })
      const url = URL.createObjectURL(res.data)
      blobRegistry.push(url)
      previewImageUrl.value = url
    } else if (tab === 'audio' && hasAudioUrls.value) {
      const u = artifacts.value.media.audios[0].url
      const res = await api.get(`/executions/${id}/export/proxy`, {
        params: { url: u },
        responseType: 'blob',
        timeout: 120000,
      })
      const url = URL.createObjectURL(res.data)
      blobRegistry.push(url)
      previewAudioUrl.value = url
    } else if (tab === 'video' && hasVideoUrls.value) {
      const u = artifacts.value.media.videos[0].url
      const res = await api.get(`/executions/${id}/export/proxy`, {
        params: { url: u },
        responseType: 'blob',
        timeout: 120000,
      })
      const url = URL.createObjectURL(res.data)
      blobRegistry.push(url)
      previewVideoUrl.value = url
    }
  } catch {
    ElMessage.warning('预览加载失败（可尝试直接下载）')
  }
}

function triggerBlobDownload(blob: Blob, filename: string) {
  const href = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  a.click()
  URL.revokeObjectURL(href)
}

async function downloadArticle(format: 'txt' | 'docx') {
  const id = store.executionId
  if (!id) return
  try {
    const res = await api.get(`/executions/${id}/export/article`, {
      params: { format },
      responseType: 'blob',
    })
    triggerBlobDownload(res.data, `flowly-${id}.${format}`)
    ElMessage.success('已开始下载')
  } catch (err: unknown) {
    const ax = err as { response?: { data?: Blob } }
    let msg = '下载失败'
    if (ax.response?.data instanceof Blob) {
      msg = await ax.response.data.text()
    }
    ElMessage.error(msg)
  }
}

async function downloadImageFromUrl(format: string) {
  const id = store.executionId
  if (!id) return
  try {
    const res = await api.get(`/executions/${id}/export/image`, {
      params: { format },
      responseType: 'blob',
      timeout: 120000,
    })
    const ext = format === 'jpeg' ? 'jpg' : format
    triggerBlobDownload(res.data, `flowly-${id}.${ext}`)
    ElMessage.success('已开始下载')
  } catch (err: unknown) {
    const ax = err as { response?: { data?: Blob } }
    let msg = '下载失败'
    if (ax.response?.data instanceof Blob) {
      msg = await ax.response.data.text()
    }
    ElMessage.error(msg)
  }
}

async function downloadAiImage(format: 'png' | 'jpeg' | 'webp') {
  const id = store.executionId
  if (!id) return
  genImageLoading.value = true
  try {
    const res = await api.get(`/executions/${id}/export/image-generated`, {
      params: { format },
      responseType: 'blob',
      timeout: 180000,
    })
    const ext = format === 'jpeg' ? 'jpg' : format
    triggerBlobDownload(res.data, `flowly-${id}-ai.${ext}`)
    ElMessage.success('已开始下载')
  } catch (err: unknown) {
    const ax = err as { response?: { data?: Blob } }
    let msg = '文生图失败（需 OPENAI_API_KEY）'
    if (ax.response?.data instanceof Blob) {
      msg = await ax.response.data.text()
    }
    ElMessage.error(msg)
  } finally {
    genImageLoading.value = false
  }
}

async function downloadTts(format: string) {
  const id = store.executionId
  if (!id) return
  ttsLoading.value = true
  try {
    const res = await api.post(
      `/executions/${id}/media/tts`,
      { voice: 'alloy', format },
      { responseType: 'blob', timeout: 120000 }
    )
    triggerBlobDownload(res.data, `flowly-${id}.${format}`)
    ElMessage.success('已开始下载')
  } catch (err: unknown) {
    const ax = err as { response?: { data?: Blob } }
    let msg = 'TTS 失败（需 OPENSPEECH_APPID/OPENSPEECH_ACCESS_TOKEN）'
    if (ax.response?.data instanceof Blob) {
      msg = await ax.response.data.text()
    }
    ElMessage.error(msg)
  } finally {
    ttsLoading.value = false
  }
}

async function downloadProxyMedia(kind: 'audio' | 'video') {
  const id = store.executionId
  if (!id || !artifacts.value) return
  const list = kind === 'audio' ? artifacts.value.media.audios : artifacts.value.media.videos
  const u = list[0]?.url
  if (!u) return
  try {
    const res = await api.get(`/executions/${id}/export/proxy`, {
      params: { url: u },
      responseType: 'blob',
      timeout: 300000,
    })
    const ext = kind === 'audio' ? 'audio' : 'mp4'
    triggerBlobDownload(res.data, `flowly-${id}.${ext}`)
    ElMessage.success('已开始下载')
  } catch {
    ElMessage.error('下载失败')
  }
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

  .node-activity {
    font-size: 12px;
    color: #444444;
    line-height: 1.45;
    margin-bottom: 4px;
  }

  .node-model-route {
    font-size: 11px;
    color: #888888;
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

.export-panel {
  margin-top: 12px;
  padding: 12px;
  border-top: 1px solid #f0f0f0;
  max-height: 420px;
  overflow: auto;
}

.export-panel-title {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 8px;
  color: #111;
}

.export-alert {
  margin-bottom: 8px;
}

.preview-tabs {
  :deep(.el-tabs__content) {
    padding: 8px 0 0;
  }
}

.export-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.preview-media img {
  max-width: 100%;
  border-radius: 4px;
  border: 1px solid #eee;
}

.preview-audio,
.preview-video {
  width: 100%;
  margin-top: 4px;
}
</style>
