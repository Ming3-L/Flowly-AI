<template>
  <div class="knowledge-base-view">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">知识库</h2>
        <span class="workflow-badge">
          <el-icon><Link /></el-icon>
          {{ workflowName }}
        </span>
      </div>
      <div class="header-actions">
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <el-button type="primary" @click="showUploadDialog = true">
          <el-icon><Upload /></el-icon>
          上传文档
        </el-button>
      </div>
    </div>

    <!-- 统计区 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">总文档</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.ready }}</div>
          <div class="stat-label">已就绪</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.processing }}</div>
          <div class="stat-label">处理中</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.totalChunks }}</div>
          <div class="stat-label">总块数</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索 -->
    <el-card class="search-card">
      <el-input
        v-model="searchQuery"
        placeholder="搜索知识库内容..."
        size="large"
        clearable
        @keyup.enter="doSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
        <template #append>
          <el-button :loading="searching" @click="doSearch">搜索</el-button>
        </template>
      </el-input>

      <!-- 搜索结果 -->
      <div v-if="searchResults.length > 0" class="search-results">
        <div class="results-header">
          找到 {{ searchResults.length }} 条相关结果
        </div>
        <div
          v-for="(result, idx) in searchResults"
          :key="idx"
          class="result-item"
        >
          <div class="result-meta">
            <el-tag size="small">{{ result.metadata?.filename || '未知' }}</el-tag>
            <span class="result-score">相关度: {{ (1 - result.score).toFixed(2) }}</span>
          </div>
          <div class="result-content">{{ result.content }}</div>
        </div>
      </div>

      <div v-else-if="searched && searchQuery && searchResults.length === 0" class="no-results">
        <el-empty description="未找到相关内容" />
      </div>
    </el-card>

    <!-- 文档表格 -->
    <el-card class="documents-card">
      <template #header>
        <div class="card-header">
          <span>文档列表</span>
          <div class="card-actions">
            <el-button size="small" type="danger" plain @click="handleBatchDelete" :disabled="selectedDocs.length === 0">
              <el-icon><Delete /></el-icon>
              批量删除 ({{ selectedDocs.length }})
            </el-button>
            <el-button size="small" type="primary" plain @click="fetchDocuments">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="documents"
        v-loading="loading"
        stripe
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="40" />
        <el-table-column label="文件名" min-width="200">
          <template #default="{ row }">
            <div class="doc-name-cell">
              <el-icon class="doc-icon">
                <Document v-if="row.file_type === 'pdf'" />
                <Document v-else-if="row.file_type === 'docx'" />
                <Document v-else />
              </el-icon>
              <span>{{ row.filename }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="file_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.file_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="块数" width="80" align="center" />
        <el-table-column prop="file_size" label="大小" width="100" align="center">
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="processing_status" label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-progress
              v-if="!row.is_ready && row.processing_status !== 'failed'"
              :percentage="processingProgress(row.processing_status)"
              :status="row.processing_status === 'embedding' ? 'warning' : undefined"
              :stroke-width="4"
              size="small"
            />
            <el-tag
              v-else-if="row.is_ready"
              size="small"
              type="success"
            >
              就绪
            </el-tag>
            <el-tag
              v-else-if="row.processing_status === 'failed'"
              size="small"
              type="danger"
            >
              失败
            </el-tag>
            <el-tag v-else size="small" type="warning">
              {{ statusLabel(row.processing_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              link
              @click="handlePreview(row)"
            >
              预览
            </el-button>
            <el-button
              size="small"
              type="danger"
              link
              :disabled="row.processing_status === 'pending'"
              @click="confirmDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper" v-if="totalDocuments > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="totalDocuments"
          layout="prev, pager, next"
          @current-change="fetchDocuments"
        />
      </div>
    </el-card>

    <!-- 上传弹窗 -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传文档"
      width="520px"
      @closed="clearUpload"
    >
      <el-form label-position="top">
        <el-form-item label="选择文件">
          <el-upload
            ref="uploadRef"
            drag
            :auto-upload="false"
            :limit="10"
            :accept="acceptTypes"
            :on-change="handleFileChange"
            :file-list="fileList"
            multiple
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div>拖拽文件到此处，或 <em>点击上传</em></div>
            <template #tip>
              <div class="upload-tip">
                支持: PDF, DOCX, TXT, HTML, Markdown, CSV (最大 50MB/文件)
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>

      <!-- 上传进度 -->
      <div v-if="uploadQueue.length > 0" class="upload-queue">
        <div class="queue-header">上传队列</div>
        <div v-for="item in uploadQueue" :key="item.name" class="queue-item">
          <span class="queue-name">{{ item.name }}</span>
          <el-progress
            v-if="item.progress > 0"
            :percentage="item.progress"
            :stroke-width="4"
            size="small"
          />
          <el-tag v-else size="small" type="warning">等待中</el-tag>
        </div>
      </div>

      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="uploading"
          :disabled="fileList.length === 0"
          @click="handleUpload"
        >
          上传 ({{ fileList.length }})
        </el-button>
      </template>
    </el-dialog>

    <!-- 预览弹窗 -->
    <el-dialog
      v-model="showPreview"
      :title="previewDoc?.filename || '文档预览'"
      width="700px"
    >
      <div v-if="previewContent" class="preview-content">
        {{ previewContent }}
      </div>
      <el-skeleton v-else :rows="5" animated />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Upload, UploadFilled, ArrowLeft, Link, Search, Refresh,
  Document, Delete,
} from '@element-plus/icons-vue'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()

const workflowId = computed(() => Number(route.params.id))

const workflowName = ref('加载中...')
const documents = ref<any[]>([])
const loading = ref(false)
const uploading = ref(false)
const searching = ref(false)
const searched = ref(false)
const searchResults = ref<any[]>([])
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalDocuments = ref(0)
const showUploadDialog = ref(false)
const selectedFile = ref<File | null>(null)
const fileList = ref<any[]>([])
const uploadRef = ref()
const selectedDocs = ref<any[]>([])
const uploadQueue = ref<Array<{ name: string; progress: number }>>([])
const showPreview = ref(false)
const previewDoc = ref<any | null>(null)
const previewContent = ref('')

const stats = computed(() => {
  const ready = documents.value.filter((d) => d.is_ready).length
  const processing = documents.value.filter(
    (d) => !d.is_ready && d.processing_status !== 'failed'
  ).length
  const totalChunks = documents.value.reduce((sum, d) => sum + (d.chunk_count || 0), 0)
  return {
    total: documents.value.length,
    ready,
    processing,
    totalChunks,
  }
})

const acceptTypes = '.pdf,.docx,.txt,.html,.md,.csv'

async function fetchWorkflowName() {
  try {
    const res = await api.get(`/workflows/${workflowId.value}`)
    workflowName.value = res.data.name
  } catch {
    workflowName.value = `工作流 #${workflowId.value}`
  }
}

async function fetchDocuments() {
  loading.value = true
  try {
    const res = await api.get(`/documents/${workflowId.value}`, {
      params: { page: currentPage.value, page_size: pageSize.value },
    })
    documents.value = res.data.items
    totalDocuments.value = res.data.total
  } catch {
    ElMessage.error('加载文档列表失败')
  } finally {
    loading.value = false
  }
}

async function doSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  searched.value = true
  try {
    const res = await api.post(`/documents/${workflowId.value}/search`, null, {
      params: { query: searchQuery.value, top_k: 10 },
    })
    searchResults.value = res.data.results
  } catch {
    ElMessage.error('搜索失败')
  } finally {
    searching.value = false
  }
}

function handleFileChange(file: any) {
  selectedFile.value = file.raw
  fileList.value.push(file)
}

function clearUpload() {
  selectedFile.value = null
  fileList.value = []
  uploadRef.value?.clearFiles()
  uploadQueue.value = []
}

async function handleUpload() {
  if (fileList.value.length === 0) return
  uploading.value = true

  // 构建上传队列
  uploadQueue.value = fileList.value.map((f: any) => ({ name: f.name, progress: 0 }))

  for (let i = 0; i < fileList.value.length; i++) {
    const fileItem = fileList.value[i]
    const queueItem = uploadQueue.value[i]
    try {
      const formData = new FormData()
      formData.append('file', fileItem.raw)

      await api.post(`/documents/upload?workflow_id=${workflowId.value}`, formData, {
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            queueItem.progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          }
        },
      })
      queueItem.progress = 100
    } catch (err: any) {
      ElMessage.error(`文件 ${fileItem.name} 上传失败: ${err?.response?.data?.detail || err.message}`)
    }
  }

  uploading.value = false
  ElMessage.success('文档上传完成，正在处理中...')
  showUploadDialog.value = false
  clearUpload()
  await fetchDocuments()
}

function handleSelectionChange(rows: any[]) {
  selectedDocs.value = rows
}

async function handleBatchDelete() {
  if (selectedDocs.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedDocs.value.length} 个文档吗？`,
      '批量删除',
      { type: 'warning' }
    )
    await Promise.all(
      selectedDocs.value.map((doc) => api.delete(`/documents/${workflowId.value}/${doc.id}`))
    )
    ElMessage.success(`已删除 ${selectedDocs.value.length} 个文档`)
    selectedDocs.value = []
    await fetchDocuments()
  } catch {
    // 已取消
  }
}

async function confirmDelete(doc: any) {
  await ElMessageBox.confirm(
    `确定删除文档 "${doc.filename}"？删除后无法恢复。`,
    '确认删除',
    { type: 'warning' }
  )
  try {
    await api.delete(`/documents/${workflowId.value}/${doc.id}`)
    ElMessage.success('文档已删除')
    await fetchDocuments()
  } catch {
    ElMessage.error('删除失败')
  }
}

async function handlePreview(doc: any) {
  previewDoc.value = doc
  showPreview.value = true
  previewContent.value = ''
  try {
    const res = await api.get(`/documents/${workflowId.value}/${doc.id}/content`)
    previewContent.value = res.data.content || '无内容'
  } catch {
    previewContent.value = '预览加载失败'
  }
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '等待中',
    chunking: '分块中',
    embedding: '嵌入中',
    completed: '完成',
    failed: '失败',
  }
  return map[status] || status
}

function processingProgress(status: string) {
  const map: Record<string, number> = {
    pending: 10,
    chunking: 50,
    embedding: 80,
  }
  return map[status] || 0
}

function formatSize(bytes?: number) {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}

function goBack() {
  router.push(`/workflows/${workflowId.value}`)
}

onMounted(() => {
  fetchWorkflowName()
  fetchDocuments()
})
</script>

<style scoped lang="scss">
.knowledge-base-view {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  background: #ffffff;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .page-title {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: #000000;
  }

  .workflow-badge {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    color: #666666;
    background: #f5f5f5;
    padding: 4px 10px;
    border-radius: 20px;
  }

  .header-actions {
    display: flex;
    gap: 8px;
  }
}

.stats-row {
  margin-bottom: 16px;

  .stat-card {
    text-align: center;

    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: #000000;
    }

    .stat-label {
      font-size: 12px;
      color: #666666;
      margin-top: 4px;
    }
  }
}

.search-card {
  margin-bottom: 16px;

  .search-results {
    margin-top: 16px;

    .results-header {
      font-size: 13px;
      color: #666666;
      margin-bottom: 12px;
    }

    .result-item {
      padding: 12px;
      background: #fafafa;
      border: 1px solid #f0f0f0;
      border-radius: 4px;
      margin-bottom: 8px;

      .result-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;

        .result-score {
          font-size: 12px;
          color: #666666;
        }
      }

      .result-content {
        font-size: 13px;
        color: #333333;
        line-height: 1.6;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        line-clamp: 3;
        -webkit-box-orient: vertical;
      }
    }
  }

  .no-results {
    margin-top: 20px;
  }
}

.documents-card {
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .card-actions {
    display: flex;
    gap: 8px;
  }

  .doc-name-cell {
    display: flex;
    align-items: center;
    gap: 8px;

    .doc-icon {
      font-size: 16px;
      color: #333333;
    }
  }

  .pagination-wrapper {
    margin-top: 16px;
    display: flex;
    justify-content: center;
  }
}

.upload-icon {
  font-size: 48px;
  color: #999999;
  margin-bottom: 8px;
}

.upload-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #666666;
}

.upload-queue {
  margin-top: 16px;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  padding: 12px;

  .queue-header {
    font-size: 13px;
    font-weight: 600;
    color: #333333;
    margin-bottom: 10px;
  }

  .queue-item {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;

    &:last-child {
      margin-bottom: 0;
    }

    .queue-name {
      flex: 1;
      font-size: 13px;
      color: #333333;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    :deep(.el-progress) {
      width: 200px;
    }
  }
}

.preview-content {
  font-size: 13px;
  line-height: 1.7;
  color: #333333;
  max-height: 60vh;
  overflow-y: auto;
  white-space: pre-wrap;
  background: #fafafa;
  padding: 16px;
  border-radius: 4px;
}
</style>
