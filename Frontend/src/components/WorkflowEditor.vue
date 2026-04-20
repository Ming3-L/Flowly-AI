<template>
  <div class="workflow-editor" @keydown="handleKeyDown" tabindex="0">
    <!-- Toolbar -->
    <div class="editor-toolbar">
      <div class="toolbar-group">
        <el-button-group>
          <el-button size="small" :icon="ZoomIn" @click="zoomIn" title="放大" />
          <el-button size="small" @click="fitView" title="适应内容">
            {{ Math.round(currentZoom * 100) }}%
          </el-button>
          <el-button size="small" :icon="ZoomOut" @click="zoomOut" title="缩小" />
        </el-button-group>
        <el-button size="small" :icon="QuestionFilled" @click="showShortcuts = true" title="快捷键">
          快捷键
        </el-button>
      </div>
      <div class="toolbar-group">
        <el-button size="small" :icon="RefreshLeft" @click="runAutoLayout" title="自动布局">
          自动布局
        </el-button>
        <el-button
          size="small"
          :icon="Delete"
          @click="deleteSelected"
          :disabled="!editorStore.selectedNodeId && !editorStore.selectedEdgeId"
          title="删除选中"
        >
          删除
        </el-button>
        <el-button
          v-if="editorStore.selectedNodeId"
          size="small"
          :icon="CopyDocument"
          @click="duplicateSelected"
          title="复制节点"
        >
          复制
        </el-button>
      </div>
      <div class="toolbar-group">
        <el-button size="small" :icon="Refresh" @click="clearCanvas" title="清空画布">
          清空
        </el-button>
        <el-button size="small" type="primary" :icon="Check" @click="handleSave" :loading="saving">
          保存
        </el-button>
      </div>
    </div>

    <!-- Main layout: palette + canvas + inspector -->
    <div class="editor-body">
      <!-- Node Palette (left sidebar) -->
      <div class="node-palette">
        <div class="palette-title">节点</div>
        <div
          v-for="(meta, type) in NODE_TYPE_META"
          :key="type"
          class="palette-item"
          draggable="true"
          @dragstart="onPaletteDragStart($event, type as EditorNodeType)"
          @click="addNodeCenter(type as EditorNodeType)"
          :title="meta.description"
        >
          <div class="palette-icon" :style="{ background: meta.color }">
            <el-icon><component :is="getIcon(meta.icon)" /></el-icon>
          </div>
          <span>{{ meta.label }}</span>
        </div>
      </div>

      <!-- Vue Flow Canvas -->
      <div
        ref="canvasContainerRef"
        class="canvas-container"
        @drop="onDrop"
        @dragover.prevent
        @dragenter.prevent
      >
        <VueFlow
          :nodes="vueFlowNodes"
          :edges="vueFlowEdges"
          :node-types="nodeTypes"
          :edge-types="edgeTypes"
          :default-viewport="{ x: 100, y: 100, zoom: 1 }"
          :connection-line-style="{ stroke: '#000000', strokeWidth: 2 }"
          :snap-to-grid="true"
          :snap-grid="[20, 20]"
          fit-view-on-init
          @nodes-change="onNodesChange"
          @edges-change="onEdgesChange"
          @connect="onConnect"
          @pane-click="onPaneClick"
          @node-click="onNodeClick"
          @edge-click="onEdgeClick"
          @node-drag-stop="onNodeDragStop"
          @move-end="onMoveEnd"
        >
          <Background :variant="BackgroundVariant.Dots" :gap="20" :size="1.5" />
          <Controls position="bottom-right" />
        </VueFlow>

        <!-- Empty state overlay -->
        <div v-if="editorStore.nodes.length === 0" class="empty-canvas">
          <el-icon :size="48" color="#999999"><component :is="getIcon('Edit')" /></el-icon>
          <p>从左侧拖放节点到这里</p>
          <p class="hint">或点击节点类型添加</p>
        </div>
      </div>

      <!-- Inspector Panel (right sidebar) -->
      <div class="node-inspector" :class="{ open: editorStore.selectedNode }">
        <template v-if="editorStore.selectedNode">
          <div class="inspector-header">
            <span class="inspector-title">节点属性</span>
            <el-button
              size="small"
              link
              :icon="Close"
              @click="editorStore.selectNode(null)"
            />
          </div>

          <!-- Label -->
          <div class="inspector-field">
            <label>名称</label>
            <el-input
              v-model="inspectorLabel"
              size="small"
              placeholder="节点名称"
              @change="updateNodeLabel"
            />
          </div>

          <!-- Type-specific config -->
          <template v-if="editorStore.selectedNode.type === 'chat'">
            <div class="inspector-field">
              <label>系统提示词</label>
              <el-input
                v-model="inspectorConfig.systemPrompt"
                type="textarea"
                :rows="4"
                size="small"
                placeholder="You are a helpful assistant."
                @change="updateNodeConfig"
              />
            </div>
            <div class="inspector-field">
              <label>模型</label>
              <el-select v-model="inspectorConfig.model" size="small" @change="updateNodeConfig">
                <el-option label="GPT-4o" value="gpt-4o" />
                <el-option label="GPT-4o Mini" value="gpt-4o-mini" />
                <el-option label="GPT-4 Turbo" value="gpt-4-turbo" />
                <el-option label="Claude 3.5 Sonnet" value="claude-3-5-sonnet" />
                <el-option label="Claude 3 Opus" value="claude-3-opus" />
                <el-option label="Ollama" value="ollama" />
              </el-select>
            </div>
            <div class="inspector-field">
              <label>温度</label>
              <el-slider
                v-model="inspectorConfig.temperature"
                :min="0"
                :max="2"
                :step="0.1"
                :show-tooltip="true"
                size="small"
                @change="updateNodeConfig"
              />
            </div>
          </template>

          <template v-else-if="editorStore.selectedNode.type === 'tool'">
            <div class="inspector-field">
              <label>工具</label>
              <el-select v-model="inspectorConfig.toolName" size="small" @change="updateNodeConfig">
                <el-option label="数据库查询" value="query_database" />
                <el-option label="外部 API" value="call_external_api" />
                <el-option label="发送通知" value="send_notification" />
              </el-select>
            </div>
            <div class="inspector-field">
              <label>工具参数 (JSON)</label>
              <el-input
                :model-value="JSON.stringify(inspectorConfig.toolParams || {}, null, 2)"
                type="textarea"
                :rows="3"
                size="small"
                placeholder='{"key": "value"}'
                @change="updateToolParams"
              />
            </div>
          </template>

          <template v-else-if="editorStore.selectedNode.type === 'condition'">
            <div class="inspector-field">
              <label>条件表达式</label>
              <el-input
                v-model="inspectorConfig.conditionExpression"
                type="textarea"
                :rows="3"
                size="small"
                placeholder="e.g. context.amount > 100"
                @change="updateNodeConfig"
              />
              <div class="field-hint">可用变量: context, user_input, workflow_state</div>
            </div>
          </template>

          <template v-else-if="editorStore.selectedNode.type === 'human_approval'">
            <div class="inspector-field">
              <label>审批问题</label>
              <el-input
                v-model="inspectorConfig.approvalQuestion"
                type="textarea"
                :rows="3"
                size="small"
                placeholder="Do you want to proceed?"
                @change="updateNodeConfig"
              />
            </div>
          </template>

          <template v-else-if="editorStore.selectedNode.type === 'parallel'">
            <div class="inspector-field">
              <label>并行分支（逗号分隔）</label>
              <el-input
                :model-value="(inspectorConfig.parallelBranches ?? []).join(', ')"
                type="textarea"
                :rows="2"
                size="small"
                placeholder="branch_a, branch_b"
                @change="updateParallelBranches"
              />
            </div>
          </template>

          <!-- Node ID -->
          <div class="inspector-field">
            <label>ID</label>
            <code class="node-id">{{ editorStore.selectedNode.id }}</code>
          </div>

          <!-- Delete -->
          <div class="inspector-actions">
            <el-button type="danger" size="small" plain @click="deleteSelected">
              删除节点
            </el-button>
          </div>
        </template>
        <template v-else>
          <div class="inspector-empty">
            <p>选择节点以编辑属性</p>
          </div>
        </template>
      </div>
    </div>

    <!-- Keyboard Shortcuts Dialog -->
    <el-dialog
      v-model="showShortcuts"
      title="快捷键"
      width="400px"
    >
      <div class="shortcuts-list">
        <div class="shortcut-group">
          <div class="shortcut-title">通用</div>
          <div class="shortcut-item">
            <kbd>Ctrl</kbd> + <kbd>S</kbd>
            <span>保存</span>
          </div>
          <div class="shortcut-item">
            <kbd>Ctrl</kbd> + <kbd>L</kbd>
            <span>自动布局</span>
          </div>
          <div class="shortcut-item">
            <kbd>Ctrl</kbd> + <kbd>D</kbd>
            <span>复制节点</span>
          </div>
          <div class="shortcut-item">
            <kbd>Delete</kbd> / <kbd>Backspace</kbd>
            <span>删除选中</span>
          </div>
          <div class="shortcut-item">
            <kbd>Esc</kbd>
            <span>取消选择</span>
          </div>
        </div>
        <div class="shortcut-group">
          <div class="shortcut-title">视图操作</div>
          <div class="shortcut-item">
            <kbd>+</kbd> / <kbd>-</kbd>
            <span>放大 / 缩小</span>
          </div>
          <div class="shortcut-item">
            <kbd>0</kbd>
            <span>适应画布</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ZoomIn,
  ZoomOut,
  RefreshLeft,
  Delete,
  Refresh,
  Check,
  Close,
  QuestionFilled,
  CopyDocument,
  ChatDotRound,
  Tools,
  Connection as ConnectionIcon,
  CircleCheck,
  CopyDocument as CopyDocumentIcon,
  Edit,
} from '@element-plus/icons-vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import { Background, BackgroundVariant } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/controls/dist/style.css'

import { useWorkflowEditorStore } from '@/stores/workflowEditor'
import type { EditorNodeType } from '@/types/workflow-editor'
import { NODE_TYPE_META } from '@/types/workflow-editor'
import BaseNode from './nodes/BaseNode.vue'
import StyledEdge from './edges/StyledEdge.vue'
import {
  editorNodesToVueFlow,
  editorEdgesToVueFlow,
  createNodePair,
  connectionToEditorEdge,
} from '@/utils/vueFlowBridge'
import type { NodeChange, EdgeChange, Connection } from '@vue-flow/core'
import type { NodeMouseEvent, EdgeMouseEvent, NodeDragEvent } from '@vue-flow/core'

interface Props {
  workflowId?: number | null
  initialName?: string
  initialDescription?: string
  initialDefinition?: any
  onSave?: (data: { name: string; description: string; definition: any }) => Promise<void>
}

const props = withDefaults(defineProps<Props>(), {
  workflowId: null,
  initialName: '',
  initialDescription: '',
  initialDefinition: () => ({}),
  onSave: undefined,
})

const editorStore = useWorkflowEditorStore()
const canvasContainerRef = ref<HTMLElement>()
const saving = ref(false)
const showShortcuts = ref(false)

// ── Vue Flow composable ───────────────────────────────────────────────────────

const {
  zoomIn: vfZoomIn,
  zoomOut: vfZoomOut,
  fitView: vfFitView,
  project,
  removeNodes,
  removeEdges,
  viewport: viewportRef,
} = useVueFlow()

const currentZoom = computed(() => viewportRef.value.zoom)

// ── Node / edge type registries ───────────────────────────────────────────────

const nodeTypes = { base: BaseNode } as any
const edgeTypes = { smoothstep: StyledEdge } as any

// ── Converted nodes / edges for Vue Flow ──────────────────────────────────────

const vueFlowNodes = computed(() => editorNodesToVueFlow(editorStore.nodes))
const vueFlowEdges = computed(() => editorEdgesToVueFlow(editorStore.edges))

// ── Inspector state ───────────────────────────────────────────────────────────

const inspectorLabel = ref('')
const inspectorConfig = ref<Record<string, any>>({})

watch(
  () => editorStore.selectedNode,
  (node) => {
    if (node) {
      inspectorLabel.value = node.label
      inspectorConfig.value = { ...node.config }
    }
  }
)

// ── Icon resolution ───────────────────────────────────────────────────────────

const iconMap: Record<string, any> = {
  ChatDotRound,
  Tools,
  Connection: ConnectionIcon,
  CircleCheck,
  CopyDocument: CopyDocumentIcon,
  Edit,
}

function getIcon(name: string) {
  return iconMap[name] ?? Edit
}

// ── Vue Flow event handlers ───────────────────────────────────────────────────

function onNodesChange(changes: NodeChange[]) {
  for (const change of changes) {
    if (change.type === 'position' && change.position) {
      editorStore.moveNode(change.id, change.position.x, change.position.y)
    }
  }
}

function onEdgesChange(changes: EdgeChange[]) {
  for (const change of changes) {
    if (change.type === 'remove') {
      editorStore.removeEdge(change.id)
    }
  }
}

function onConnect(connection: Connection) {
  const edge = connectionToEditorEdge(connection)
  const created = editorStore.createEdge(
    edge.sourceNodeId,
    edge.sourcePortId,
    edge.targetNodeId,
    edge.targetPortId
  )
  if (!created) {
    ElMessage.warning('该连接已存在')
  }
}

function onPaneClick() {
  editorStore.clearSelection()
}

function onNodeClick(_event: NodeMouseEvent) {
  editorStore.selectNode(_event.node.id)
}

function onEdgeClick(_event: EdgeMouseEvent) {
  editorStore.selectEdge(_event.edge.id)
}

function onNodeDragStop(_event: NodeDragEvent) {
  editorStore.moveNode(_event.node.id, _event.node.position.x, _event.node.position.y)
}

function onMoveEnd() {}

// ── Zoom / fit helpers ────────────────────────────────────────────────────────

function zoomIn() { vfZoomIn() }
function zoomOut() { vfZoomOut() }

function fitView() {
  vfFitView({ padding: 0.2, duration: 300 })
}

// ── Node palette ──────────────────────────────────────────────────────────────

function onPaletteDragStart(e: DragEvent, type: EditorNodeType) {
  e.dataTransfer?.setData('application/vueflow-node', type)
  e.dataTransfer!.effectAllowed = 'copy'
}

function onDrop(event: DragEvent) {
  const type = event.dataTransfer?.getData('application/vueflow-node') as EditorNodeType | null
  if (!type) return

  const bounds = canvasContainerRef.value!.getBoundingClientRect()
  const position = project({
    x: event.clientX - bounds.left,
    y: event.clientY - bounds.top,
  })

  const { editor } = createNodePair(type, position)
  editorStore.nodes.push(editor)
  editorStore.hasUnsavedChanges = true
}

function addNodeCenter(type: EditorNodeType) {
  const bounds = canvasContainerRef.value?.getBoundingClientRect()
  if (!bounds) return

  const vp = viewportRef.value
  const cx = (bounds.width / 2 - vp.x) / vp.zoom
  const cy = (bounds.height / 2 - vp.y) / vp.zoom

  const { editor } = createNodePair(type, { x: cx - 100, y: cy - 40 })
  editorStore.nodes.push(editor)
  editorStore.hasUnsavedChanges = true
}

// ── Auto layout ──────────────────────────────────────────────────────────────

function runAutoLayout() {
  editorStore.autoLayout()
  editorStore.hasUnsavedChanges = true
  nextTick(() => {
    fitView()
  })
}

// ── Actions ──────────────────────────────────────────────────────────────────

function deleteSelected() {
  if (editorStore.selectedNodeId) {
    const nodeId = editorStore.selectedNodeId
    editorStore.selectNode(null)
    removeNodes([nodeId])
    editorStore.removeNode(nodeId)
  } else if (editorStore.selectedEdgeId) {
    const edgeId = editorStore.selectedEdgeId
    editorStore.selectEdge(null)
    removeEdges([edgeId])
    editorStore.removeEdge(edgeId)
  }
}

function duplicateSelected() {
  if (editorStore.selectedNodeId) {
    const node = editorStore.nodes.find((n) => n.id === editorStore.selectedNodeId)
    if (!node) return
    const copy = editorStore.duplicateNode(editorStore.selectedNodeId)
    if (copy) {
      editorStore.selectNode(copy.id)
      nextTick(() => fitView())
    }
  }
}

function updateNodeLabel() {
  if (editorStore.selectedNodeId) {
    editorStore.updateNode(editorStore.selectedNodeId, { label: inspectorLabel.value })
  }
}

function updateNodeConfig() {
  if (editorStore.selectedNodeId) {
    editorStore.updateNodeConfig(editorStore.selectedNodeId, inspectorConfig.value)
  }
}

function updateToolParams(val: string) {
  try {
    inspectorConfig.value.toolParams = JSON.parse(val)
    updateNodeConfig()
  } catch {
    ElMessage.error('参数格式错误，请输入有效 JSON')
  }
}

function updateParallelBranches(val: string) {
  inspectorConfig.value.parallelBranches = val.split(',').map((s) => s.trim()).filter(Boolean)
  updateNodeConfig()
}

function clearCanvas() {
  editorStore.clear()
}

// ── Keyboard shortcuts ───────────────────────────────────────────────────────

function handleKeyDown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    handleSave()
    e.preventDefault()
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
    runAutoLayout()
    e.preventDefault()
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
    duplicateSelected()
    e.preventDefault()
  }
  if (e.key === 'Delete' || e.key === 'Backspace') {
    const tag = (document.activeElement as HTMLElement)?.tagName
    if (tag !== 'INPUT' && tag !== 'TEXTAREA') {
      deleteSelected()
    }
  }
  if (e.key === 'Escape') {
    editorStore.clearSelection()
  }
  if (e.key === '+' || e.key === '=') {
    zoomIn()
    e.preventDefault()
  }
  if (e.key === '-') {
    zoomOut()
    e.preventDefault()
  }
  if (e.key === '0') {
    fitView()
    e.preventDefault()
  }
}

// ── Save ──────────────────────────────────────────────────────────────────────

async function handleSave() {
  if (!editorStore.isValid) {
    ElMessage.error(editorStore.validationErrors[0] || '工作流验证失败')
    return
  }

  saving.value = true
  try {
    const data = {
      name: props.initialName || 'Untitled Workflow',
      description: props.initialDescription || '',
      definition: editorStore.definition,
    }

    if (props.onSave) {
      await props.onSave(data)
    }
    editorStore.hasUnsavedChanges = false
    ElMessage.success('保存成功')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// ── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(() => {
  if (props.initialDefinition && props.initialDefinition.nodes) {
    editorStore.loadFromDefinition(props.initialDefinition)
  } else {
    editorStore.clear()
  }
  canvasContainerRef.value?.focus()
})

onUnmounted(() => {
  editorStore.clear()
})
</script>

<style scoped lang="scss">
.workflow-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  outline: none;
  overflow: hidden;
}

// ── Toolbar ───────────────────────────────────────────────────────────────────

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #ffffff;
  border-bottom: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 6px;

  &:not(:last-child)::after {
    content: '';
    display: block;
    width: 1px;
    height: 20px;
    background: #e0e0e0;
    margin-left: 6px;
  }
}

// ── Body ──────────────────────────────────────────────────────────────────────

.editor-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

// ── Palette ───────────────────────────────────────────────────────────────────

.node-palette {
  width: 160px;
  flex-shrink: 0;
  background: #fafafa;
  border-right: 1px solid #e0e0e0;
  padding: 12px 8px;
  overflow-y: auto;
}

.palette-title {
  font-size: 11px;
  font-weight: 600;
  color: #666666;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 10px;
  padding: 0 4px;
}

.palette-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  margin-bottom: 4px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
  user-select: none;

  &:hover {
    background: #f0f0f0;
  }

  &:active {
    background: #e4e4e4;
  }
}

.palette-icon {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  .el-icon {
    font-size: 16px;
    color: #ffffff;
  }
}

.palette-item span {
  font-size: 13px;
  font-weight: 500;
  color: #000000;
}

// ── Canvas ─────────────────────────────────────────────────────────────────────

.canvas-container {
  flex: 1;
  background: #ffffff;
  overflow: hidden;
  position: relative;

  :deep(.vue-flow) {
    width: 100%;
    height: 100%;
  }

  :deep(.vue-flow__background) {
    background: #ffffff;
  }

  :deep(.vue-flow__minimap) {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    box-shadow: 0px 1px 3px rgba(0, 0, 0, 0.08);
  }

  :deep(.vue-flow__controls) {
    box-shadow: 0px 1px 3px rgba(0, 0, 0, 0.08);
    border-radius: 4px;
    overflow: hidden;
    border: 1px solid #e0e0e0;

    .vue-flow__controls-button {
      background: #ffffff;
      border: none;
      border-bottom: 1px solid #e8e8e8;
      width: 28px;
      height: 28px;
      cursor: pointer;

      &:last-child {
        border-bottom: none;
      }

      &:hover {
        background: #f5f5f5;
      }

      svg {
        fill: #333333;
        max-width: 14px;
        max-height: 14px;
      }
    }
  }
}

// ── Inspector ──────────────────────────────────────────────────────────────────

.node-inspector {
  width: 0;
  overflow: hidden;
  transition: width 0.2s ease;
  background: #ffffff;
  border-left: 1px solid #e0e0e0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;

  &.open {
    width: 300px;
  }
}

.inspector-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.inspector-title {
  font-size: 14px;
  font-weight: 600;
  color: #000000;
}

.inspector-field {
  padding: 10px 16px;

  label {
    display: block;
    font-size: 12px;
    font-weight: 500;
    color: #333333;
    margin-bottom: 6px;
  }

  .el-input,
  .el-select {
    width: 100%;
  }

  :deep(.el-slider) {
    margin-top: 4px;
  }
}

.field-hint {
  margin-top: 4px;
  font-size: 11px;
  color: #999999;
}

.node-id {
  font-size: 11px;
  color: #666666;
  background: #fafafa;
  padding: 2px 6px;
  border-radius: 3px;
  word-break: break-all;
}

.inspector-actions {
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;
  margin-top: auto;
}

.inspector-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999999;
  font-size: 13px;
  text-align: center;
  padding: 20px;
}

// ── Shortcuts Dialog ───────────────────────────────────────────────────────

.shortcuts-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.shortcut-group {
  .shortcut-title {
    font-size: 13px;
    font-weight: 600;
    color: #000000;
    margin-bottom: 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid #f0f0f0;
  }
}

.shortcut-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 13px;

  kbd {
    background: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 12px;
    font-family: monospace;
    color: #333333;
  }

  span {
    color: #666666;
    font-size: 12px;
  }
}

// ── Empty canvas ─────────────────────────────────────────────────────────────

.empty-canvas {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;

  p {
    margin: 8px 0 0;
    color: #666666;
    font-size: 14px;
  }

  .hint {
    margin-top: 4px;
    font-size: 12px;
    color: #999999;
  }
}
</style>
