<template>
  <el-card class="workflow-runner" shadow="never">
    <template #header>
      <div class="runner-header">
        <span>工作流执行</span>
        <el-tag v-if="store.currentWorkflow" size="small">
          {{ store.currentWorkflow.name }}
        </el-tag>
      </div>
    </template>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @submit.prevent="handleSubmit"
    >
      <!-- Workflow Selector -->
      <el-form-item label="工作流" prop="workflowId">
        <el-select
          v-model="form.workflowId"
          placeholder="选择工作流"
          filterable
          clearable
          :loading="store.isLoading"
          class="full-width"
          :disabled="store.isRunning"
          @change="onWorkflowChange"
        >
          <el-option
            v-for="wf in store.workflows"
            :key="wf.id"
            :label="wf.name"
            :value="wf.id"
          >
            <div class="workflow-option">
              <span class="workflow-name">{{ wf.name }}</span>
              <span class="workflow-desc">{{ wf.description || '—' }}</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- Prompt Input -->
      <el-form-item label="查询" prop="query">
        <el-input
          v-model="form.query"
          type="textarea"
          :rows="4"
          placeholder="描述任务或提出问题…"
          maxlength="2000"
          show-word-limit
          resize="vertical"
          :disabled="store.isRunning"
          @keydown.ctrl.enter="handleSubmit"
        />
      </el-form-item>

      <!-- Context (optional) -->
      <el-form-item label="上下文（可选）" prop="context">
        <el-input
          v-model="form.contextText"
          type="textarea"
          :rows="2"
          placeholder='以 JSON 格式提供额外上下文，如 {"key": "value"}'
          :disabled="store.isRunning"
        />
      </el-form-item>

      <!-- Submit -->
      <el-form-item class="submit-row">
        <div class="actions">
          <el-button
            type="primary"
            :loading="store.isRunning"
            :disabled="!form.workflowId || !form.query.trim()"
            size="large"
            @click="handleSubmit"
          >
            <el-icon v-if="!store.isRunning"><VideoPlay /></el-icon>
            {{ store.isRunning ? '运行中…' : '运行工作流' }}
          </el-button>

          <el-button
            v-if="store.hasActiveThread"
            text
            @click="handleReset"
          >
            <el-icon><RefreshLeft /></el-icon>
            重置
          </el-button>
        </div>
      </el-form-item>
    </el-form>

    <!-- Error display -->
    <el-alert
      v-if="store.errorMessage"
      :title="store.errorMessage"
      type="error"
      show-icon
      :closable="false"
      class="runner-error"
    />
  </el-card>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { VideoPlay, RefreshLeft } from '@element-plus/icons-vue'
import { useWorkflowStore } from '@/stores/workflow'
import type { FormInstance, FormRules } from 'element-plus'

const store = useWorkflowStore()
const formRef = ref<FormInstance>()

// ── Form State ────────────────────────────────────────────────────────────────

const form = reactive({
  workflowId: null as number | null,
  query: '',
  contextText: '',
})

// ── Validation Rules ───────────────────────────────────────────────────────────

const rules: FormRules = {
  workflowId: [
    { required: true, message: '请选择一个工作流', trigger: 'change' },
  ],
  query: [
    { required: true, message: '请输入查询内容', trigger: 'blur' },
    {
      min: 2,
      max: 2000,
      message: '查询内容长度为 2-2000 个字符',
      trigger: 'blur',
    },
  ],
}

// ── Handlers ──────────────────────────────────────────────────────────────────

function onWorkflowChange(id: number) {
  const wf = store.workflows.find((w) => w.id === id) ?? null
  store.currentWorkflow = wf
}

async function handleSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()

    let context: Record<string, any> = {}
    if (form.contextText.trim()) {
      try {
        context = JSON.parse(form.contextText.trim())
      } catch {
        // Treat as plain string context
        context = { raw: form.contextText.trim() }
      }
    }

    await store.startWorkflow({
      workflow_id: form.workflowId!,
      query: form.query.trim(),
      context,
    })
  } catch {
    // Validation errors shown inline by Element Plus
  }
}

function handleReset() {
  store.resetExecutionState()
  formRef.value?.resetFields()
  form.contextText = ''
}
</script>

<style scoped lang="scss">
.workflow-runner {
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.runner-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 14px;
  color: #000000;
}

.full-width {
  width: 100%;
}

.workflow-option {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .workflow-name {
    font-weight: 600;
    color: #000000;
  }

  .workflow-desc {
    font-size: 12px;
    color: #666666;
  }
}

.submit-row {
  margin-bottom: 0;

  .actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }
}

.runner-error {
  margin-top: 12px;
}
</style>
