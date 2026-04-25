<template>
  <el-card class="workflow-runner" shadow="never">
    <template #header>
      <div class="runner-header">
        <span>{{ ui.t('wf.runner.header') }}</span>
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
      <el-form-item :label="ui.t('wf.runner.workflowLabel')" prop="workflowId">
        <el-select
          v-model="form.workflowId"
          :placeholder="ui.t('wf.runner.workflowPlaceholder')"
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
              <span class="workflow-desc">{{ wf.description || ui.t('wf.common.descNone') }}</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <!-- Prompt Input -->
      <el-form-item :label="ui.t('wf.runner.queryLabel')" prop="query">
        <el-input
          v-model="form.query"
          type="textarea"
          :rows="4"
          :placeholder="ui.t('wf.runner.queryPlaceholder')"
          maxlength="2000"
          show-word-limit
          resize="vertical"
          :disabled="store.isRunning"
          @keydown.ctrl.enter="handleSubmit"
        />
      </el-form-item>

      <!-- Multi-modal attachments -->
      <el-form-item label="附件（图片/音频/视频）">
        <el-upload
          v-model:file-list="fileList"
          :auto-upload="false"
          :multiple="true"
          :limit="6"
          :disabled="store.isRunning"
          accept="image/*,audio/*,video/*"
          drag
          class="full-width"
        >
          <el-icon><UploadFilled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到这里，或 <em>点击选择</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持图片/音频/视频；最多 6 个文件（单个文件大小由服务端限制）。
            </div>
          </template>
        </el-upload>
      </el-form-item>

      <!-- Context (optional) -->
      <el-form-item :label="ui.t('wf.runner.contextLabel')" prop="context">
        <el-input
          v-model="form.contextText"
          type="textarea"
          :rows="2"
          :placeholder="ui.t('wf.runner.contextPlaceholder')"
          :disabled="store.isRunning"
        />
      </el-form-item>

      <!-- 费用与画布对齐：可选，对应后端 CostRecord.client_node_id -->
      <el-form-item :label="ui.t('wf.runner.clientNodeLabel')" prop="clientNodeId">
        <el-input
          v-model="form.clientNodeId"
          :placeholder="ui.t('wf.runner.clientNodePlaceholder')"
          maxlength="128"
          show-word-limit
          clearable
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
            {{ store.isRunning ? ui.t('wf.runner.submitRunning') : ui.t('wf.runner.submit') }}
          </el-button>

          <el-button
            v-if="store.hasActiveThread"
            text
            @click="handleReset"
          >
            <el-icon><RefreshLeft /></el-icon>
            {{ ui.t('wf.runner.reset') }}
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
import { reactive, ref, computed } from 'vue'
import { VideoPlay, RefreshLeft, UploadFilled } from '@element-plus/icons-vue'
import { useWorkflowStore } from '@/stores/workflow'
import { useUiLabelsStore } from '@/stores/uiLabels'
import type { FormInstance, FormRules } from 'element-plus'
import type { UploadUserFile } from 'element-plus'
import api from '@/utils/api'

const store = useWorkflowStore()
const ui = useUiLabelsStore()
const formRef = ref<FormInstance>()
const fileList = ref<UploadUserFile[]>([])

// ── Form State ────────────────────────────────────────────────────────────────

const form = reactive({
  workflowId: null as number | null,
  query: '',
  contextText: '',
  clientNodeId: '',
})

// ── Validation Rules ───────────────────────────────────────────────────────────

const rules = computed<FormRules>(() => ({
  workflowId: [
    { required: true, message: ui.t('wf.runner.validation.workflowRequired'), trigger: 'change' },
  ],
  query: [
    { required: true, message: ui.t('wf.runner.validation.queryRequired'), trigger: 'blur' },
    {
      min: 2,
      max: 2000,
      message: ui.t('wf.runner.validation.queryLength'),
      trigger: 'blur',
    },
  ],
}))

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

    // 上传附件（如有）
    const attachments: Array<{
      name: string
      size: number
      mime: string
      path: string
      proxy_url: string
      public_url: string
    }> = []

    for (const f of fileList.value) {
      const raw = f.raw as File | undefined
      if (!raw) continue
      const fd = new FormData()
      fd.append('file', raw)
      const res = await api.post('/media/upload', fd, {
        timeout: 120000,
      })
      attachments.push(res.data)
    }

    if (attachments.length) {
      context.attachments = attachments
    }

    const wf = store.workflows.find((w) => w.id === form.workflowId) ?? null
    const def = wf?.definition as Record<string, any> | undefined
    const nodes = def?.nodes
    const isCanvas = Array.isArray(nodes) && nodes.length > 0

    if (isCanvas) {
      await store.startCanvasWorkflow({
        workflow_id: form.workflowId!,
        query: form.query.trim(),
        context,
        initial_inputs: attachments.length ? { files: attachments } : {},
        ...(form.clientNodeId.trim()
          ? { client_node_id: form.clientNodeId.trim() }
          : {}),
      })
    } else {
      await store.startWorkflow({
        workflow_id: form.workflowId!,
        query: form.query.trim(),
        context,
        model_name: 'doubao',
        ...(form.clientNodeId.trim()
          ? { client_node_id: form.clientNodeId.trim() }
          : {}),
      })
    }
  } catch {
    // Validation errors shown inline by Element Plus
  }
}

function handleReset() {
  store.resetExecutionState()
  formRef.value?.resetFields()
  form.contextText = ''
  form.clientNodeId = ''
  fileList.value = []
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
