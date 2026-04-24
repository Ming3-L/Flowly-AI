<template>
  <div class="editor-view">
    <div class="editor-header">
      <div class="header-left">
        <el-button text @click="goBack" :icon="ArrowLeft" size="small">返回</el-button>
        <el-divider direction="vertical" />
        <el-input
          v-model="workflowName"
          class="name-input"
          placeholder="工作流名称"
          size="small"
          @change="hasChanges = true"
        />
        <el-tag v-if="workflowId" type="info" size="small">ID: {{ workflowId }}</el-tag>
      </div>
      <div class="header-right">
        <el-tag v-if="editorStore.hasUnsavedChanges" type="warning" size="small">
          未保存
        </el-tag>
        <el-tag v-else type="success" size="small">已保存</el-tag>
        <el-button type="primary" size="small" :loading="saving" @click="handleSave">
          保存
        </el-button>
      </div>
    </div>

    <WorkflowEditor
      :workflow-id="workflowId"
      :initial-name="workflowName"
      :initial-description="workflowDescription"
      :initial-definition="workflowDefinition"
      :on-save="onSave"
    />
    <WorkflowGuideFab :workflow-id="workflowId" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import WorkflowEditor from '@/components/WorkflowEditor.vue'
import WorkflowGuideFab from '@/components/workflow/WorkflowGuideFab.vue'
import { useWorkflowEditorStore } from '@/stores/workflowEditor'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()
const editorStore = useWorkflowEditorStore()

const workflowId = ref<number | null>(
  route.params.id && route.params.id !== 'new' ? Number(route.params.id) : null
)

const workflowName = ref('')
const workflowDescription = ref('')
const workflowDefinition = ref<any>({})
const saving = ref(false)
const hasChanges = ref(false)

function goBack() {
  if (editorStore.hasUnsavedChanges) {
    ElMessageBox.confirm('您有未保存的更改，确定要离开吗？', '警告', {
      confirmButtonText: '离开',
      cancelButtonText: '取消',
      type: 'warning',
    })
      .then(() => router.back())
      .catch(() => {})
  } else {
    router.back()
  }
}

async function onSave(data: { name: string; description: string; definition: any }) {
  saving.value = true
  try {
    const payload = {
      name: workflowName.value || data.name,
      description: workflowDescription.value || data.description,
      definition: data.definition,
    }

    if (workflowId.value) {
      await api.put(`/workflows/${workflowId.value}`, payload)
      hasChanges.value = false
      ElMessage.success('工作流已更新')
    } else {
      const res = await api.post('/workflows/', payload)
      workflowId.value = res.data.id
      workflowName.value = res.data.name
      hasChanges.value = false
      ElMessage.success('工作流已创建')

      // Update URL to reflect new ID
      router.replace({ name: 'WorkflowEditor', params: { id: String(workflowId.value) } })
    }
  } finally {
    saving.value = false
  }
}

async function handleSave() {
  const data = editorStore.toExport(
    workflowName.value || 'Untitled Workflow',
    workflowDescription.value
  )
  await onSave(data)
}

onMounted(async () => {
  if (workflowId.value) {
    try {
      const res = await api.get(`/workflows/${workflowId.value}`)
      const wf = res.data
      workflowName.value = wf.name
      workflowDescription.value = wf.description
      workflowDefinition.value = wf.definition || {}
    } catch {
      ElMessage.error('加载工作流失败')
      router.push('/workflows')
    }
  } else {
    // New workflow
    workflowName.value = '新工作流'
    workflowDescription.value = ''
    workflowDefinition.value = {}
  }
})

onBeforeUnmount(() => {
  // Warn if leaving with unsaved changes
  if (editorStore.hasUnsavedChanges) {
    // Just clear the store
  }
})
</script>

<style scoped lang="scss">
.editor-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: #ffffff;
  border-bottom: 1px solid #e0e0e0;
  gap: 12px;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.name-input {
  width: 260px;

  :deep(.el-input__inner) {
    font-weight: 600;
    font-size: 14px;
    color: #000000;
  }
}
</style>
