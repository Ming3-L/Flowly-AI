<template>
  <div class="workflow-detail-page">
    <!-- 页头 -->
    <div class="detail-header">
      <div class="header-left">
        <el-button text @click="$router.push('/workflows')">
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </el-button>
        <el-divider direction="vertical" />
        <div class="workflow-title">
          <h1>{{ workflow?.name ?? '加载中...' }}</h1>
          <el-tag :type="workflow?.is_active ? 'success' : 'info'" size="small">
            {{ workflow?.is_active ? '启用' : '停用' }}
          </el-tag>
        </div>
      </div>
      <div class="header-actions">
        <el-tooltip content="切换状态">
          <el-button
            :icon="Switch"
            @click="handleToggleStatus"
            :loading="togglingStatus"
          >
            {{ workflow?.is_active ? '停用' : '启用' }}
          </el-button>
        </el-tooltip>
        <el-button :icon="CopyDocument" @click="handleDuplicate">复制</el-button>
        <el-dropdown trigger="click" @command="handleExport">
          <el-button :icon="Download">
            导出
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="json">
                <el-icon><Document /></el-icon>
                导出为 JSON
              </el-dropdown-item>
              <el-dropdown-item command="copy">
                <el-icon><CopyDocument /></el-icon>
                复制定义到剪贴板
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button :icon="Edit" @click="$router.push(`/workflows/${workflowId}/edit`)">
          编辑工作流
        </el-button>
        <el-button :icon="Collection" @click="$router.push(`/workflows/${workflowId}/knowledge-base`)">
          知识库
        </el-button>
        <el-button type="primary" :icon="VideoPlay" @click="$router.push(`/run/${workflowId}`)">
          运行
        </el-button>
        <el-button type="danger" plain :icon="Delete" @click="handleDelete">删除</el-button>
      </div>
    </div>

    <!-- 内容 -->
    <div class="detail-body">
      <el-row :gutter="16">
        <!-- 左侧：信息 + 定义 -->
        <el-col :span="16">
          <!-- 信息卡片 -->
          <el-card class="info-card">
            <template #header>
              <span>基本信息</span>
              <el-button size="small" link :icon="Edit" @click="$router.push(`/workflows/${workflowId}/edit`)">
                编辑
              </el-button>
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="名称">{{ workflow?.name }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="workflow?.is_active ? 'success' : 'info'" size="small">
                  {{ workflow?.is_active ? '启用' : '停用' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">
                {{ formatDate(workflow?.created_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="更新时间">
                {{ formatDate(workflow?.updated_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="描述" :span="2">
                {{ workflow?.description || '无描述' }}
              </el-descriptions-item>
              <el-descriptions-item label="执行次数">
                {{ workflow?.execution_count ?? 0 }}
              </el-descriptions-item>
              <el-descriptions-item label="会话数">
                {{ workflow?.thread_count ?? 0 }}
              </el-descriptions-item>
              <el-descriptions-item label="节点数量">
                {{ workflow?.definition?.nodes?.length ?? 0 }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- 定义卡片 -->
          <el-card class="definition-card">
            <template #header>
              <div class="card-header-row">
                <span>工作流定义</span>
                <el-button-group size="small">
                  <el-button @click="showDefinition = 'visual'">可视化</el-button>
                  <el-button @click="showDefinition = 'json'">JSON</el-button>
                </el-button-group>
              </div>
            </template>

            <!-- 可视化预览 -->
            <div v-if="showDefinition === 'visual'" class="definition-preview">
              <div v-if="!workflow?.definition?.nodes?.length" class="empty-def">
                <el-empty description="暂无节点定义" />
              </div>
              <div v-else class="node-list">
                <div
                  v-for="node in workflow?.definition?.nodes"
                  :key="node.id"
                  class="def-node"
                >
                  <div
                    class="def-node-badge"
                    :style="{ background: NODE_TYPE_COLORS[node.type] ?? '#000000' }"
                  >
                    {{ NODE_TYPE_LABELS[node.type] ?? node.type }}
                  </div>
                  <span class="def-node-label">{{ node.label }}</span>
                  <span class="def-node-ports">
                    {{ node.ports?.length ?? 0 }} ports
                  </span>
                </div>
                <div v-if="workflow?.definition?.edges?.length" class="def-info">
                  {{ workflow.definition.edges.length }} 条连接
                </div>
              </div>
            </div>

            <!-- 结构化视图 -->
            <div v-else class="definition-json">
              <el-input
                :model-value="definitionJson"
                type="textarea"
                :rows="15"
                readonly
                class="json-editor"
              />
            </div>
          </el-card>
        </el-col>

        <!-- 右侧：执行历史 -->
        <el-col :span="8">
          <el-card class="history-card">
            <template #header>
              <div class="card-header-row">
                <span>执行历史</span>
                <el-button size="small" link :icon="Refresh" @click="fetchExecutions">
                  刷新
                </el-button>
              </div>
            </template>

            <div v-if="loadingExecutions" class="loading-state">
              <el-skeleton :rows="3" animated />
            </div>

            <div v-else-if="executions.length === 0" class="empty-history">
              <el-empty description="暂无执行记录" image-size="64" />
            </div>

            <div v-else class="execution-list">
              <div
                v-for="exec in executions"
                :key="exec.id"
                class="execution-item"
                @click="$router.push(`/run/${workflowId}?thread=${exec.thread_id}&execution=${exec.id}`)"
              >
                <div class="exec-header">
                  <el-tag :type="execStatusType(exec.status)" size="small">
                    {{ execStatusLabel(exec.status) }}
                  </el-tag>
                  <span class="exec-date">{{ formatDate(exec.started_at) }}</span>
                </div>
                <div class="exec-query">{{ exec.query }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Edit,
  VideoPlay,
  Delete,
  Refresh,
  Collection,
  Download,
  CopyDocument,
  Switch,
  ArrowDown,
  Document,
} from '@element-plus/icons-vue'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()

const workflowId = computed(() => Number(route.params.id))

const workflow = ref<any>(null)
const executions = ref<any[]>([])
const loadingExecutions = ref(false)
const showDefinition = ref<'visual' | 'json'>('visual')
const togglingStatus = ref(false)

const NODE_TYPE_COLORS: Record<string, string> = {
  chat: '#000000',
  tool: '#666666',
  condition: '#999999',
  human_approval: '#333333',
  parallel: '#b3b3b3',
}

const NODE_TYPE_LABELS: Record<string, string> = {
  chat: '对话',
  tool: '工具',
  condition: '条件',
  human_approval: '审批',
  parallel: '并行',
}

const definitionJson = computed(() => {
  try {
    return JSON.stringify(workflow.value?.definition ?? {}, null, 2)
  } catch {
    return '{}'
  }
})

function formatDate(dateStr?: string) {
  if (!dateStr) return '-'
  try {
    return new Date(dateStr).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

function execStatusType(status: string) {
  switch (status) {
    case 'completed': return 'success'
    case 'running': return 'primary'
    case 'failed': return 'danger'
    case 'pending': return 'info'
    default: return 'info'
  }
}

function execStatusLabel(status: string) {
  switch (status) {
    case 'completed': return '完成'
    case 'running': return '运行中'
    case 'failed': return '失败'
    case 'pending': return '等待'
    default: return status
  }
}

async function fetchWorkflow() {
  try {
    const res = await api.get(`/workflows/${workflowId.value}`)
    workflow.value = res.data
  } catch {
    ElMessage.error('加载工作流失败')
    router.push('/workflows')
  }
}

async function fetchExecutions() {
  loadingExecutions.value = true
  try {
    const res = await api.get('/executions/', { params: { workflow_id: workflowId.value } })
    executions.value = res.data.items ?? []
  } catch {
    executions.value = []
  } finally {
    loadingExecutions.value = false
  }
}

async function handleToggleStatus() {
  togglingStatus.value = true
  try {
    const newStatus = !workflow.value?.is_active
    await api.put(`/workflows/${workflowId.value}`, { is_active: newStatus })
    workflow.value.is_active = newStatus
    ElMessage.success(newStatus ? '工作流已启用' : '工作流已停用')
  } catch {
    ElMessage.error('状态切换失败')
  } finally {
    togglingStatus.value = false
  }
}

async function handleDuplicate() {
  try {
    const res = await api.post('/workflows/', {
      name: `${workflow.value?.name} (副本)`,
      description: workflow.value?.description,
      definition: workflow.value?.definition,
    })
    ElMessage.success('工作流已复制')
    router.push(`/workflows/${res.data.id}`)
  } catch {
    ElMessage.error('复制失败')
  }
}

function handleExport(command: string) {
  if (command === 'copy') {
    navigator.clipboard.writeText(definitionJson.value).then(() => {
      ElMessage.success('定义已复制到剪贴板')
    }).catch(() => {
      ElMessage.error('复制失败')
    })
    return
  }

  // 下载 JSON 文件
  const blob = new Blob([definitionJson.value], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${workflow.value?.name ?? 'workflow'}_definition.json`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('JSON 文件已下载')
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除工作流「${workflow.value?.name}」吗？此操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await api.delete(`/workflows/${workflowId.value}`)
    ElMessage.success('删除成功')
    router.push('/workflows')
  } catch {
    // 已取消
  }
}

onMounted(() => {
  fetchWorkflow()
  fetchExecutions()
})
</script>

<style scoped lang="scss">
.workflow-detail-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background: #ffffff;
  border-bottom: 1px solid #e0e0e0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.workflow-title {
  display: flex;
  align-items: center;
  gap: 10px;

  h1 {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
    color: #000000;
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-body {
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
}

.info-card,
.definition-card,
.history-card {
  margin-bottom: 16px;
  border-radius: 6px;
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.definition-preview {
  min-height: 120px;
}

.empty-def {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
}

.node-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.def-node {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
}

.def-node-badge {
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  color: #ffffff;
  flex-shrink: 0;
}

.def-node-label {
  font-size: 13px;
  font-weight: 500;
  color: #000000;
  flex: 1;
}

.def-node-ports {
  font-size: 11px;
  color: #666666;
}

.def-info {
  font-size: 12px;
  color: #666666;
  padding: 4px 12px;
}

.definition-json .json-editor {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
}

.execution-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 600px;
  overflow-y: auto;
}

.execution-item {
  padding: 10px;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover {
    background: #fafafa;
    border-color: #000000;
  }
}

.exec-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.exec-date {
  font-size: 11px;
  color: #666666;
}

.exec-query {
  font-size: 12px;
  color: #333333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loading-state,
.empty-history {
  padding: 20px 0;
}
</style>
