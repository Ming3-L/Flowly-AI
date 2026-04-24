<template>
  <div class="workflow-run-view">
    <el-container>
      <!-- 页头 -->
      <el-header>
        <div class="header-content">
            <el-button text @click="$router.back()">
            <el-icon><ArrowLeft /></el-icon>
            {{ ui.t('wf.run.back') }}
          </el-button>
          <h1>{{ pageTitle }}</h1>
        </div>
      </el-header>

      <!-- 主内容 -->
      <el-main>
        <el-row :gutter="20">
          <!-- 左侧：运行表单 -->
          <el-col :xs="24" :sm="24" :md="10" :lg="8">
            <WorkflowRunner />
          </el-col>

          <!-- 右侧：监控区（聊天 + 节点状态） -->
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
import { useUiLabelsStore } from '@/stores/uiLabels'
import WorkflowRunner from '@/components/WorkflowRunner.vue'
import WorkflowMonitor from '@/components/WorkflowMonitor.vue'

const route = useRoute()
const store = useWorkflowStore()
const ui = useUiLabelsStore()

// ── 标题 ───────────────────────────────────────────────────────────────────

const pageTitle = computed(() => {
  if (store.currentWorkflow) {
    return `${ui.t('wf.run.titleRunPrefix')}${store.currentWorkflow.name}`
  }
  if (route.params.id) {
    return ui.t('wf.run.titleExec')
  }
  return ui.t('wf.run.titleRun')
})

// ── 生命周期 ────────────────────────────────────────────────────────────────

onMounted(async () => {
  // 若未加载过工作流列表，则先预加载
  if (store.workflows.length === 0) {
    await store.fetchWorkflows()
  }

  // 若携带 thread（执行历史点击进入），则优先加载历史回放
  const thread = String(route.query.thread ?? '').trim()
  if (thread) {
    await store.loadThread(thread)
  }

  // 若路由携带 workflowId，则预选中对应工作流
  const workflowId = Number(route.params.id)
  if (workflowId && !isNaN(workflowId)) {
    const wf = store.workflows.find((w) => w.id === workflowId)
    if (wf) store.currentWorkflow = wf
  }
})

onUnmounted(() => {
  // 组件卸载时清理 SSE 连接
  //（store.resetExecutionState 已处理，但此处保留显式清理入口）
})

// ── 事件处理 ─────────────────────────────────────────────────────────────────

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
