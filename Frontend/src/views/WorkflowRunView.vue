<template>
  <div class="workflow-run-view">
    <el-container>
      <!-- Header -->
      <el-header>
        <div class="header-content">
            <el-button text @click="$router.back()">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <h1>{{ pageTitle }}</h1>
        </div>
      </el-header>

      <!-- Main Content -->
      <el-main>
        <el-row :gutter="20">
          <!-- Left: Runner Form -->
          <el-col :xs="24" :sm="24" :md="10" :lg="8">
            <WorkflowRunner />
          </el-col>

          <!-- Right: Monitor (Chat + Node Status) -->
          <el-col :xs="24" :sm="24" :md="14" :lg="16">
            <WorkflowMonitor @reset="onMonitorReset" />
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useWorkflowStore } from '@/stores/workflow'
import WorkflowRunner from '@/components/WorkflowRunner.vue'
import WorkflowMonitor from '@/components/WorkflowMonitor.vue'

const route = useRoute()
const store = useWorkflowStore()

// ── Title ───────────────────────────────────────────────────────────────────

const pageTitle = computed(() => {
  if (store.currentWorkflow) {
    return `运行: ${store.currentWorkflow.name}`
  }
  if (route.params.id) {
    return '工作流执行'
  }
  return '执行工作流'
})

// ── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(async () => {
  // Pre-load workflows if not already loaded
  if (store.workflows.length === 0) {
    await store.fetchWorkflows()
  }

  // If navigated with a workflow ID, pre-select it
  const workflowId = Number(route.params.id)
  if (workflowId && !isNaN(workflowId)) {
    const wf = store.workflows.find((w) => w.id === workflowId)
    if (wf) store.currentWorkflow = wf
  }
})

onUnmounted(() => {
  // Cleanup SSE connection on component unmount
  // (store's resetExecutionState handles it, but we clean explicitly here)
})

// ── Handlers ─────────────────────────────────────────────────────────────────

function onMonitorReset() {
  store.resetExecutionState()
}
</script>

<style scoped lang="scss">
.workflow-run-view {
  min-height: 100vh;
  background: #ffffff;
}

.el-header {
  background: #ffffff;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;

  .header-content {
    display: flex;
    align-items: center;
    gap: 16px;
    width: 100%;
    height: 100%;
    padding: 0 20px;

    h1 {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
      color: #000000;
    }
  }
}

.el-main {
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 0;
}
</style>
