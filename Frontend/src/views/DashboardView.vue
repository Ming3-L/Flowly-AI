<template>
  <div class="dashboard-view">
    <el-container>
      <el-header>
        <div class="header-content">
          <h1>工作流仪表盘</h1>
          <div class="header-actions">
            <el-button type="primary" @click="createDialogVisible = true">
              <el-icon><Plus /></el-icon>
              创建工作流
            </el-button>
            <el-button @click="store.fetchWorkflows()">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </el-header>

      <el-main>
        <el-row :gutter="16" class="stats-row">
          <el-col :span="6">
            <el-card shadow="hover" class="stat-card" @click="router.push('/workflows')">
              <div class="stat-content">
                <div class="stat-icon dark">
                  <el-icon><Document /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ dashboardWorkflows.length }}</div>
                  <div class="stat-label">工作流总数</div>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="stat-card" @click="router.push('/workflows?is_active=true')">
              <div class="stat-content">
                <div class="stat-icon green">
                  <el-icon><CircleCheck /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ activeCount }}</div>
                  <div class="stat-label">活跃工作流</div>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="stat-card" @click="goRunsOrObservability">
              <div class="stat-content">
                <div class="stat-icon blue">
                  <el-icon><Clock /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ history.length }}</div>
                  <div class="stat-label">最近运行</div>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="stat-card" @click="goRunsOrObservability">
              <div class="stat-content">
                <div class="stat-icon red">
                  <el-icon><CircleClose /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ recentFailures }}</div>
                  <div class="stat-label">最近失败</div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 快捷入口 -->
        <el-row :gutter="16" class="quick-actions-row">
          <el-col :span="8">
            <el-card class="quick-card" @click="router.push('/workflows/new')">
              <div class="quick-content">
                <el-icon class="quick-icon"><Edit /></el-icon>
                <span class="quick-label">创建新工作流</span>
              </div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card class="quick-card" @click="router.push('/run')">
              <div class="quick-content">
                <el-icon class="quick-icon"><VideoPlay /></el-icon>
                <span class="quick-label">运行工作流</span>
              </div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card class="quick-card" @click="router.push('/chat')">
              <div class="quick-content">
                <el-icon class="quick-icon"><ChatDotRound /></el-icon>
                <span class="quick-label">AI 对话</span>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="16">
            <el-card class="workflow-table-card" shadow="never">
              <template #header>
                <div class="card-header">
                  <span>可用工作流</span>
                  <div class="card-header-right">
                    <el-input
                      v-model="searchQuery"
                      placeholder="搜索工作流…"
                      clearable
                      size="small"
                      style="width:200px"
                    />
                    <el-button size="small" type="primary" link @click="router.push('/workflows')">
                      查看全部
                      <el-icon><ArrowRight /></el-icon>
                    </el-button>
                  </div>
                </div>
              </template>

              <el-table
                :data="filteredWorkflows"
                v-loading="store.isLoading"
                stripe
                highlight-current-row
                @row-click="handleRowClick"
              >
                <el-table-column type="index" width="60" />
                <el-table-column label="名称" min-width="180">
                  <template #default="{ row }">
                    <div class="wf-name-cell">
                      <span class="wf-name">{{ row.name }}</span>
                      <span class="wf-desc">{{ row.description || '—' }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="状态" width="120">
                  <template #default="{ row }">
                    <el-tag :type="row.is_active ? 'success' : 'info'" effect="plain" size="small">
                      {{ row.is_active ? '活跃' : '禁用' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="执行次数" width="100" align="center">
                  <template #default="{ row }">
                    <span class="exec-count">{{ row.execution_count ?? 0 }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="创建时间" width="160">
                  <template #default="{ row }">
                    <span class="date-text">{{ formatDate(row.created_at) }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="220" fixed="right">
                  <template #default="{ row }">
                    <div class="action-buttons">
                      <el-button type="primary" size="small" plain @click.stop="handleRun(row)">
                        <el-icon><VideoPlay /></el-icon>
                        运行
                      </el-button>
                      <el-button size="small" plain @click.stop="handleRowClick(row)">
                        详情
                      </el-button>
                      <el-button type="danger" size="small" plain @click.stop="handleDelete(row)">
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>

          <el-col :span="8">
            <el-card v-if="history.length > 0" class="history-card" shadow="never">
              <template #header>
                <div class="card-header">
                  <span>最近执行记录</span>
                  <el-button size="small" link @click="goRunsOrObservability">
                    {{ isPlatformStaff ? '监控' : '运行' }}
                    <el-icon><ArrowRight /></el-icon>
                  </el-button>
                </div>
              </template>
              <div class="history-list">
                <div
                  v-for="item in history.slice(0, 8)"
                  :key="item.thread_id"
                  class="history-item"
                >
                  <div class="history-header">
                    <el-tag
                      :type="historyStatusType(item.status)"
                      size="small"
                      effect="plain"
                    >
                      {{ item.status }}
                    </el-tag>
                    <span class="history-time">{{ formatDate(item.started_at) }}</span>
                  </div>
                  <div class="history-query">{{ item.query }}</div>
                </div>
              </div>
            </el-card>
            <el-card v-else class="history-card empty-card" shadow="never">
              <el-empty description="暂无执行记录" :image-size="60" />
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>

    <el-dialog v-model="createDialogVisible" title="创建工作流" width="520px">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-position="top">
        <el-form-item label="名称" prop="name">
          <el-input v-model="createForm.name" placeholder="我的工作流" maxlength="255" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="简要描述…"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="isCreating" @click="handleCreateSubmit">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import {
  Plus, Refresh, Document, CircleCheck, Clock, VideoPlay,
  Delete, CircleClose, Edit, ChatDotRound, ArrowRight,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useWorkflowStore } from '@/stores/workflow'
import { useAuthStore } from '@/stores/auth'
import type { Workflow } from '@/types'
import api from '@/utils/api'

const router = useRouter()
const store = useWorkflowStore()
const auth = useAuthStore()
const { workflows, history } = storeToRefs(store)

const isPlatformStaff = computed(() => !!(auth.user?.is_staff || auth.user?.is_superuser))

function goRunsOrObservability() {
  if (isPlatformStaff.value) router.push('/observability')
  else router.push('/run')
}

const searchQuery = ref('')

/** 仪表盘「可用工作流」仅展示当前用户自己的；管理员在列表页查看全站。 */
const dashboardWorkflows = computed(() => {
  if (!isPlatformStaff.value) return workflows.value
  const uid = auth.user?.id
  if (uid == null) return workflows.value
  return workflows.value.filter(
    (w) => (w as Workflow).owner_user_id == null || (w as Workflow).owner_user_id === uid
  )
})

const filteredWorkflows = computed(() => {
  const q = searchQuery.value.toLowerCase()
  const base = dashboardWorkflows.value
  const list = q
    ? base.filter(
        (w) =>
          w.name.toLowerCase().includes(q) ||
          (w.description ?? '').toLowerCase().includes(q)
      )
    : base.slice(0, 10)
  return list
})

const activeCount = computed(() => dashboardWorkflows.value.filter((w) => w.is_active).length)
const recentFailures = computed(() => history.value.filter((h) => h.status === 'failed').length)

function handleRowClick(row: Workflow) {
  router.push(`/workflows/${row.id}`)
}

function handleRun(row: Workflow) {
  store.currentWorkflow = row
  router.push({ name: 'WorkflowRun', params: { id: String(row.id) } })
}

async function handleDelete(row: Workflow) {
  if (isPlatformStaff.value) {
    const uid = auth.user?.id
    if (uid != null && row.owner_user_id != null && row.owner_user_id !== uid) {
      ElMessage.warning('不能删除其他用户的工作流')
      return
    }
  }
  try {
    await ElMessageBox.confirm(
      `确定删除工作流 "${row.name}" 吗？`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await api.delete(`/workflows/${row.id}`)
    ElMessage.success('已删除')
    store.fetchWorkflows()
  } catch (err: any) {
    if (err !== 'cancel') {
      ElMessage.error(err?.response?.data?.detail ?? '删除失败')
    }
  }
}

const createDialogVisible = ref(false)
const isCreating = ref(false)
const createFormRef = ref()

const createForm = reactive({
  name: '',
  description: '',
  definition: { nodes: [] as unknown[] },
})

const createRules = {
  name: [{ required: true, message: '请输入工作流名称', trigger: 'blur' }],
}

async function handleCreateSubmit() {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
    isCreating.value = true
    await api.post('/workflows/', createForm)
    ElMessage.success('创建成功')
    createDialogVisible.value = false
    createFormRef.value.resetFields()
    store.fetchWorkflows()
    router.push('/workflows')
  } catch {
    // 校验错误会在表单内联显示
  } finally {
    isCreating.value = false
  }
}

function formatDate(dateStr: string | Date): string {
  const d = typeof dateStr === 'string' ? new Date(dateStr) : dateStr
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function historyStatusType(status: string): string {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
  }
  return map[status] ?? 'info'
}

store.fetchWorkflows()
</script>

<style scoped lang="scss">
.dashboard-view {
  min-height: 100vh;
  background: var(--app-bg);
}

.el-header {
  background: var(--app-surface);
  border-bottom: 1px solid var(--app-border);

  .header-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 100%;
    padding: 0 20px;

    h1 {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
      color: var(--app-text);
      letter-spacing: -0.2px;
    }

    .header-actions {
      display: flex;
      gap: 8px;
    }
  }
}

.el-main {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-row {
  .stat-card {
    border-radius: 6px;
    border: 1px solid var(--app-border);
    cursor: pointer;
    transition: box-shadow 0.15s;

    &:hover {
      box-shadow: 0 4px 12px rgba(0,0,0,0.12) !important;
    }

    .stat-content {
      display: flex;
      align-items: center;
      gap: 12px;

      .stat-icon {
        width: 44px;
        height: 44px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        flex-shrink: 0;

        &.dark { background: var(--app-text); color: var(--app-surface); }
        &.green { background: var(--app-accent-success); color: #0d0f14; }
        &.blue { background: var(--app-accent-info); color: #0d0f14; }
        &.red { background: var(--app-accent-danger); color: #0d0f14; }
      }

      .stat-info {
        .stat-value {
          font-size: 24px;
          font-weight: 700;
          color: var(--app-text);
          line-height: 1.2;
          font-variant-numeric: tabular-nums;
        }

        .stat-label {
          font-size: 12px;
          color: var(--app-text-3);
          margin-top: 2px;
        }
      }
    }
  }
}

.quick-actions-row {
  .quick-card {
    border-radius: 6px;
    border: 1px solid var(--app-border);
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;

    &:hover {
      border-color: var(--app-text-3);
      background: var(--el-fill-color-light);
    }

    .quick-content {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 8px 0;

      .quick-icon {
        font-size: 20px;
        color: var(--app-text);
      }

      .quick-label {
        font-size: 14px;
        font-weight: 500;
        color: var(--app-text);
      }
    }
  }
}

.workflow-table-card,
.history-card {
  border-radius: 6px;
  border: 1px solid var(--app-border);

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: 600;
    font-size: 14px;
    color: var(--app-text);
  }

  .card-header-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }
}

.wf-name-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .wf-name {
    font-weight: 600;
    color: var(--app-text);
    font-size: 14px;
  }

  .wf-desc {
    font-size: 12px;
    color: var(--app-text-3);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 200px;
  }
}

.exec-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text);
}

.date-text {
  font-size: 12px;
  color: var(--app-text-3);
}

.action-buttons {
  display: flex;
  gap: 6px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 500px;
  overflow-y: auto;
}

.history-item {
  padding: 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;

  .history-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
  }

  .history-time {
    font-size: 11px;
    color: var(--app-text-3);
  }

  .history-query {
    font-size: 12px;
    color: var(--app-text-2);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.empty-card {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
