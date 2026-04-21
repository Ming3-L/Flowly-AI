<template>
  <div class="workflow-list-page">
    <!-- Header -->
    <div class="list-header">
      <h1>工作流</h1>
      <div class="header-actions">
        <el-button
          v-if="selectedRows.length > 0"
          type="danger"
          plain
          size="small"
          @click="handleBatchDelete"
        >
          批量删除 ({{ selectedRows.length }})
        </el-button>
        <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">
          新建工作流
        </el-button>
      </div>
    </div>

    <!-- Search & Filter -->
    <div class="list-toolbar">
      <el-input
        v-model="search"
        placeholder="搜索工作流..."
        :prefix-icon="Search"
        clearable
        class="search-input"
        @input="debouncedFetch"
      />
      <el-select
        v-model="filterActive"
        placeholder="状态"
        clearable
        style="width: 140px"
        @change="fetchWorkflows"
      >
        <el-option label="启用" :value="true" />
        <el-option label="停用" :value="false" />
      </el-select>
    </div>

    <!-- Table -->
    <div class="list-content">
      <el-table
        :data="workflows"
        v-loading="isLoading"
        stripe
        class="workflow-table"
        @row-click="handleRowClick"
        :row-class-name="() => 'clickable-row'"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="40" />
        <el-table-column label="名称" min-width="200">
          <template #default="{ row }">
            <div class="workflow-name-cell">
              <span class="wf-name">{{ row.name }}</span>
              <span v-if="row.description" class="wf-desc">{{ row.description }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="执行次数" width="100" align="center">
          <template #default="{ row }">
            <el-badge :value="row.execution_count ?? 0" :max="999" />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            <span class="date-cell">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="160">
          <template #default="{ row }">
            <span class="date-cell">{{ formatDate(row.updated_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-btns" @click.stop>
              <el-button
                type="primary"
                link
                size="small"
                :icon="View"
                @click="handleView(row)"
              >
                查看
              </el-button>
              <el-button
                type="warning"
                link
                size="small"
                :icon="Edit"
                @click="handleEdit(row)"
              >
                编辑
              </el-button>
              <el-button
                type="success"
                link
                size="small"
                :icon="CopyDocument"
                @click="handleDuplicate(row)"
              >
                复制
              </el-button>
              <el-button
                type="danger"
                link
                size="small"
                :icon="Delete"
                @click="handleDelete(row)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- Empty state -->
      <div v-if="!isLoading && workflows.length === 0" class="empty-state">
        <el-empty description="暂无工作流">
          <el-button type="primary" @click="showCreateDialog = true">创建第一个工作流</el-button>
        </el-empty>
      </div>

      <!-- Pagination -->
      <div v-if="total > pageSize" class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="fetchWorkflows"
        />
      </div>
    </div>

    <!-- Create Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      title="新建工作流"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-position="top"
      >
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="createForm.name"
            placeholder="例如：客户支持工作流"
            maxlength="255"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="简要描述此工作流的用途..."
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">
          创建并编辑
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, View, Edit, Delete, CopyDocument } from '@element-plus/icons-vue'
import api from '@/utils/api'

const router = useRouter()

const workflows = ref<any[]>([])
const isLoading = ref(false)
const search = ref('')
const filterActive = ref<boolean | null>(null)
const currentPage = ref(1)
const pageSize = 15
const total = ref(0)
const selectedRows = ref<any[]>([])

const showCreateDialog = ref(false)
const creating = ref(false)
const createFormRef = ref()

const createForm = ref({
  name: '',
  description: '',
})

const createRules = {
  name: [
    { required: true, message: '请输入工作流名称', trigger: 'blur' },
    { min: 1, max: 255, message: '名称长度 1-255', trigger: 'blur' },
  ],
}

let searchTimer: ReturnType<typeof setTimeout> | null = null

function debouncedFetch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    fetchWorkflows()
  }, 300)
}

async function fetchWorkflows() {
  isLoading.value = true
  try {
    const params: Record<string, any> = {
      search: search.value || undefined,
      is_active: filterActive.value,
    }
    const res = await api.get('/workflows/', { params })
    workflows.value = res.data.items ?? res.data ?? []
    total.value = res.data.total ?? workflows.value.length
  } catch {
    workflows.value = []
  } finally {
    isLoading.value = false
  }
}

async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    const res = await api.post('/workflows/', {
      name: createForm.value.name,
      description: createForm.value.description,
      definition: { version: '1.0', nodes: [], edges: [] },
    })
    const wfId = res.data.id
    showCreateDialog.value = false
    createForm.value = { name: '', description: '' }
    ElMessage.success('工作流已创建')
    router.push(`/workflows/${wfId}/edit`)
  } catch {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

function handleView(row: any) {
  router.push(`/workflows/${row.id}`)
}

function handleEdit(row: any) {
  router.push(`/workflows/${row.id}/edit`)
}

function handleRowClick(row: any) {
  router.push(`/workflows/${row.id}`)
}

async function handleDuplicate(row: any) {
  try {
    await api.post('/workflows/', {
      name: `${row.name} (副本)`,
      description: row.description,
      definition: row.definition,
    })
    ElMessage.success('工作流已复制')
    fetchWorkflows()
  } catch {
    ElMessage.error('复制失败')
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(
      `确定要删除工作流「${row.name}」吗？`,
      '删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await api.delete(`/workflows/${row.id}`)
    ElMessage.success('删除成功')
    fetchWorkflows()
  } catch {
    // cancelled
  }
}

function handleSelectionChange(rows: any[]) {
  selectedRows.value = rows
}

async function handleBatchDelete() {
  if (selectedRows.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedRows.value.length} 个工作流吗？此操作不可恢复。`,
      '批量删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await Promise.all(
      selectedRows.value.map((row) => api.delete(`/workflows/${row.id}`))
    )
    ElMessage.success(`已删除 ${selectedRows.value.length} 个工作流`)
    selectedRows.value = []
    fetchWorkflows()
  } catch {
    // cancelled
  }
}

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

onMounted(fetchWorkflows)
</script>

<style scoped lang="scss">
.workflow-list-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: #ffffff;
  border-bottom: 1px solid #e0e0e0;

  h1 {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
    color: #000000;
  }
}

.list-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  background: #ffffff;
  border-bottom: 1px solid #e0e0e0;
}

.search-input {
  max-width: 320px;
}

.list-content {
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
}

.workflow-table {
  border-radius: 6px;
  overflow: hidden;

  :deep(.clickable-row) {
    cursor: pointer;
  }

  :deep(.el-table__row) {
    transition: background 0.15s;

    &:hover td {
      background: #fafafa !important;
    }
  }
}

.workflow-name-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .wf-name {
    font-weight: 600;
    color: #000000;
    font-size: 14px;
  }

  .wf-desc {
    font-size: 12px;
    color: #666666;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 300px;
  }
}

.date-cell {
  font-size: 12px;
  color: #666666;
}

.action-btns {
  display: flex;
  align-items: center;
  gap: 4px;
}

.empty-state {
  padding: 60px 0;
}

.pagination {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}
</style>
