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
        <el-button
          v-if="editorStore.selectedNodeId && props.workflowId"
          size="small"
          type="success"
          plain
          :icon="VideoPlay"
          title="同步调试当前节点（POST /workflows/canvas-node/run，计费对齐 client_node_id）"
          @click="handleRunSelectedNode"
        >
          调试节点
        </el-button>
      </div>
      <div class="toolbar-group">
        <el-button size="small" :icon="Refresh" @click="clearCanvas" title="清空画布">
          清空
        </el-button>
        <el-button
          v-if="props.workflowId"
          size="small"
          type="primary"
          plain
          :icon="VideoPlay"
          @click="handleRunCanvas"
          title="按画布 edges 串联执行，并通过 WebSocket 推送节点进度"
        >
          运行画布
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
              <div class="field-tools">
                <el-button size="small" @click="openEnhance('systemPrompt')">AI 加工</el-button>
              </div>
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
              <label>AI 模型</label>
              <el-select
                v-model="inspectorConfig.modelKey"
                filterable
                clearable
                placeholder="沿用节点已保存配置（旧版）"
                size="small"
                popper-class="wf-model-catalog-popper"
                @change="onInspectorModelKeyChange"
              >
                <el-option label="沿用节点已保存配置（旧版）" value="" />
                <el-option-group
                  v-for="(grp, gidx) in modelOptionGroupsForInspector"
                  :key="`chat-grp-${gidx}-${grp.label}`"
                  :label="grp.label"
                >
                  <el-option
                    v-for="row in grp.rows"
                    :key="`chat-${row.key}`"
                    :label="row.label"
                    :value="row.key"
                    :title="row.scope_summary || row.description || ''"
                  >
                    <div class="model-opt-title">
                      {{ row.label }}
                      <span v-if="row.has_custom_credentials" class="model-own-key">自有密钥</span>
                    </div>
                    <div class="model-opt-desc">{{ row.scope_summary || row.description }}</div>
                    <div v-if="row.scopes?.length" class="model-opt-tags">
                      <span v-for="(t, ti) in row.scopes" :key="ti" class="model-opt-tag">{{ t }}</span>
                    </div>
                  </el-option>
                </el-option-group>
              </el-select>
              <div class="field-hint">按分类查看适用范围；清空表示沿用旧版 provider/model。</div>
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

          <template v-else-if="editorStore.selectedNode.type === 'text'">
            <div class="inspector-field">
              <label>处理方式</label>
              <el-select v-model="inspectorConfig.processMode" size="small" @change="updateNodeConfig">
                <el-option label="AI 处理（调用大模型）" value="llm" />
                <el-option label="仅模板拼接（不调模型）" value="template" />
              </el-select>
            </div>
            <div class="inspector-field">
              <label>AI 模型</label>
              <el-select
                v-model="inspectorConfig.modelKey"
                filterable
                clearable
                placeholder="沿用节点已保存配置（旧版）"
                size="small"
                popper-class="wf-model-catalog-popper"
                @change="onInspectorModelKeyChange"
              >
                <el-option label="沿用节点已保存配置（旧版）" value="" />
                <el-option-group
                  v-for="(grp, gidx) in modelOptionGroupsForInspector"
                  :key="`text-grp-${gidx}-${grp.label}`"
                  :label="grp.label"
                >
                  <el-option
                    v-for="row in grp.rows"
                    :key="`text-${row.key}`"
                    :label="row.label"
                    :value="row.key"
                    :title="row.scope_summary || row.description || ''"
                  >
                    <div class="model-opt-title">
                      {{ row.label }}
                      <span v-if="row.has_custom_credentials" class="model-own-key">自有密钥</span>
                    </div>
                    <div class="model-opt-desc">{{ row.scope_summary || row.description }}</div>
                    <div v-if="row.scopes?.length" class="model-opt-tags">
                      <span v-for="(t, ti) in row.scopes" :key="ti" class="model-opt-tag">{{ t }}</span>
                    </div>
                  </el-option>
                </el-option-group>
              </el-select>
              <div class="field-hint">按分类查看适用范围；清空表示保留旧版 provider/model。</div>
            </div>
            <div class="inspector-field">
              <label>系统提示词</label>
              <div class="field-tools">
                <el-button size="small" @click="openEnhance('systemPrompt')">AI 加工</el-button>
              </div>
              <el-input
                v-model="inspectorConfig.systemPrompt"
                type="textarea"
                :rows="3"
                size="small"
                placeholder="你是助手。"
                @change="updateNodeConfig"
              />
            </div>
            <div class="inspector-field">
              <label>默认指令</label>
              <div class="field-tools">
                <el-button size="small" @click="openEnhance('prompt')">AI 加工</el-button>
              </div>
              <el-input
                v-model="inspectorConfig.prompt"
                type="textarea"
                :rows="3"
                size="small"
                placeholder="例如：请对下方文本进行摘要。"
                @change="updateNodeConfig"
              />
              <div v-if="inspectorConfig.processMode !== 'template'" v-pre class="field-hint">
                画布会把上游节点输出写入本节点的「输入」；未写 {{input}} 时也会自动附在指令前传给模型。
              </div>
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
            <div class="inspector-field">
              <label>Max tokens</label>
              <el-input-number
                v-model="inspectorConfig.max_tokens"
                :min="64"
                :max="8192"
                :step="64"
                size="small"
                @change="updateNodeConfig"
              />
            </div>
          </template>

          <template v-else-if="editorStore.selectedNode.type === 'image'">
            <div class="inspector-field">
              <label>AI 模型</label>
              <el-select
                v-model="inspectorConfig.modelKey"
                filterable
                clearable
                placeholder="沿用节点已保存配置（旧版）"
                size="small"
                popper-class="wf-model-catalog-popper"
                @change="onInspectorModelKeyChange"
              >
                <el-option label="沿用节点已保存配置（旧版）" value="" />
                <el-option-group
                  v-for="(grp, gidx) in modelOptionGroupsForInspector"
                  :key="`img-grp-${gidx}-${grp.label}`"
                  :label="grp.label"
                >
                  <el-option
                    v-for="row in grp.rows"
                    :key="`img-${row.key}`"
                    :label="row.label"
                    :value="row.key"
                    :title="row.scope_summary || row.description || ''"
                  >
                    <div class="model-opt-title">
                      {{ row.label }}
                      <span v-if="row.has_custom_credentials" class="model-own-key">自有密钥</span>
                    </div>
                    <div class="model-opt-desc">{{ row.scope_summary || row.description }}</div>
                    <div v-if="row.scopes?.length" class="model-opt-tags">
                      <span v-for="(t, ti) in row.scopes" :key="ti" class="model-opt-tag">{{ t }}</span>
                    </div>
                  </el-option>
                </el-option-group>
              </el-select>
              <div class="field-hint">按分类查看适用范围；清空表示保留旧版 provider/model。</div>
            </div>
            <div class="inspector-field">
              <label>图片 URL（可选）</label>
              <el-input
                v-model="inspectorConfig.image_url"
                size="small"
                placeholder="https://example.com/image.png"
                @change="updateNodeConfig"
              />
            </div>
            <div class="inspector-field">
              <label>默认提问/描述</label>
              <div class="field-tools">
                <el-button size="small" @click="openEnhance('captionPrompt')">AI 加工</el-button>
              </div>
              <el-input
                v-model="inspectorConfig.captionPrompt"
                type="textarea"
                :rows="3"
                size="small"
                placeholder="请简要描述这张图片的主要内容。"
                @change="updateNodeConfig"
              />
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
            <div class="inspector-field">
              <label>Max tokens</label>
              <el-input-number
                v-model="inspectorConfig.max_tokens"
                :min="64"
                :max="8192"
                :step="64"
                size="small"
                @change="updateNodeConfig"
              />
            </div>
          </template>

          <template v-else-if="editorStore.selectedNode.type === 'audio'">
            <div class="inspector-field">
              <label>AI 模型（摘要用 LLM）</label>
              <el-select
                v-model="inspectorConfig.modelKey"
                filterable
                clearable
                placeholder="沿用节点已保存配置（旧版）"
                size="small"
                popper-class="wf-model-catalog-popper"
                @change="onInspectorModelKeyChange"
              >
                <el-option label="沿用节点已保存配置（旧版）" value="" />
                <el-option-group
                  v-for="(grp, gidx) in modelOptionGroupsForInspector"
                  :key="`aud-grp-${gidx}-${grp.label}`"
                  :label="grp.label"
                >
                  <el-option
                    v-for="row in grp.rows"
                    :key="`aud-${row.key}`"
                    :label="row.label"
                    :value="row.key"
                    :title="row.scope_summary || row.description || ''"
                  >
                    <div class="model-opt-title">
                      {{ row.label }}
                      <span v-if="row.has_custom_credentials" class="model-own-key">自有密钥</span>
                    </div>
                    <div class="model-opt-desc">{{ row.scope_summary || row.description }}</div>
                    <div v-if="row.scopes?.length" class="model-opt-tags">
                      <span v-for="(t, ti) in row.scopes" :key="ti" class="model-opt-tag">{{ t }}</span>
                    </div>
                  </el-option>
                </el-option-group>
              </el-select>
            </div>
            <div class="inspector-field">
              <label>音频 URL（可选，需 OPENAI_API_KEY 做 Whisper 转写）</label>
              <el-input
                v-model="inspectorConfig.audio_url"
                size="small"
                placeholder="https://example.com/audio.mp3"
                @change="updateNodeConfig"
              />
            </div>
            <div class="inspector-field">
              <label>系统提示词</label>
              <div class="field-tools">
                <el-button size="small" @click="openEnhance('systemPrompt')">AI 加工</el-button>
              </div>
              <el-input
                v-model="inspectorConfig.systemPrompt"
                type="textarea"
                :rows="3"
                size="small"
                @change="updateNodeConfig"
              />
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
            <div class="inspector-field">
              <label>Max tokens</label>
              <el-input-number
                v-model="inspectorConfig.max_tokens"
                :min="64"
                :max="8192"
                :step="64"
                size="small"
                @change="updateNodeConfig"
              />
            </div>
          </template>

          <template v-else-if="editorStore.selectedNode.type === 'video'">
            <div class="inspector-field">
              <label>AI 模型</label>
              <el-select
                v-model="inspectorConfig.modelKey"
                filterable
                clearable
                placeholder="沿用节点已保存配置（旧版）"
                size="small"
                popper-class="wf-model-catalog-popper"
                @change="onInspectorModelKeyChange"
              >
                <el-option label="沿用节点已保存配置（旧版）" value="" />
                <el-option-group
                  v-for="(grp, gidx) in modelOptionGroupsForInspector"
                  :key="`vid-grp-${gidx}-${grp.label}`"
                  :label="grp.label"
                >
                  <el-option
                    v-for="row in grp.rows"
                    :key="`vid-${row.key}`"
                    :label="row.label"
                    :value="row.key"
                    :title="row.scope_summary || row.description || ''"
                  >
                    <div class="model-opt-title">
                      {{ row.label }}
                      <span v-if="row.has_custom_credentials" class="model-own-key">自有密钥</span>
                    </div>
                    <div class="model-opt-desc">{{ row.scope_summary || row.description }}</div>
                    <div v-if="row.scopes?.length" class="model-opt-tags">
                      <span v-for="(t, ti) in row.scopes" :key="ti" class="model-opt-tag">{{ t }}</span>
                    </div>
                  </el-option>
                </el-option-group>
              </el-select>
              <p class="inspector-video-hint">
                此节点走对话补全接口，输出为文本（脚本、分镜、镜头描述等）。Seedance 等文生视频模型在模型总表的「图像/视频/3D」分类中列出，需在控制台开通后通过专用视频 API 接入工程。
              </p>
            </div>
            <div class="inspector-field">
              <label>视频 URL（仅记录，可选）</label>
              <el-input
                v-model="inspectorConfig.video_url"
                size="small"
                placeholder="https://example.com/video.mp4"
                @change="updateNodeConfig"
              />
            </div>
            <div class="inspector-field">
              <label>系统提示词</label>
              <div class="field-tools">
                <el-button size="small" @click="openEnhance('systemPrompt')">AI 加工</el-button>
              </div>
              <el-input
                v-model="inspectorConfig.systemPrompt"
                type="textarea"
                :rows="3"
                size="small"
                @change="updateNodeConfig"
              />
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
            <div class="inspector-field">
              <label>Max tokens</label>
              <el-input-number
                v-model="inspectorConfig.max_tokens"
                :min="64"
                :max="8192"
                :step="64"
                size="small"
                @change="updateNodeConfig"
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

    <PromptEnhanceModal
      v-model="enhanceOpen"
      :workflow-id="props.workflowId"
      :client-node-id="editorStore.selectedNode?.id ?? ''"
      :node-type="editorStore.selectedNode?.type ?? ''"
      :field="enhanceField"
      :initial-value="enhanceInitialValue"
      :model-key="String((inspectorConfig as any).modelKey || 'doubao-default')"
      title="AI 加工提示词"
      @confirm="applyEnhanced"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
  VideoPlay,
  ChatDotRound,
  Tools,
  Connection as ConnectionIcon,
  CircleCheck,
  CopyDocument as CopyDocumentIcon,
  Edit,
  Document,
  PictureFilled,
  Microphone,
  VideoCamera,
} from '@element-plus/icons-vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import { Background, BackgroundVariant } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/controls/dist/style.css'

import { useWorkflowEditorStore } from '@/stores/workflowEditor'
import { useWorkflowStore } from '@/stores/workflow'
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
import api from '@/utils/api'
import type { NodeChange, EdgeChange, Connection } from '@vue-flow/core'
import type { NodeMouseEvent, EdgeMouseEvent, NodeDragEvent } from '@vue-flow/core'
import PromptEnhanceModal from '@/components/prompt/PromptEnhanceModal.vue'

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
const workflowStore = useWorkflowStore()
const canvasContainerRef = ref<HTMLElement>()
const saving = ref(false)
const showShortcuts = ref(false)
const enhanceOpen = ref(false)
const enhanceField = ref('systemPrompt')
const enhanceInitialValue = ref('')

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

/** GET /api/ai/models — 项目内置模型预设（无密钥） */
interface CatalogModelRow {
  key: string
  label: string
  description: string
  route: string
  /** project=内置；user=当前用户自定义 */
  source?: string
  category?: string
  category_label?: string
  category_order?: number
  scopes?: string[]
  scope_summary?: string
  has_custom_credentials?: boolean
  /** 仅在这些画布节点类型中可选；空或未返回表示不限制 */
  canvas_node_kinds?: string[]
  /** 为 true 时在 chat/text/image/audio/video 各节点均可选（如豆包智能路由） */
  canvas_universal?: boolean
  api_kind?: string
  /** false：仅出现在模型总表，不出现在画布 LLM 节点下拉（向量/生图/语音等） */
  show_in_canvas_llm_nodes?: boolean
}

interface ModelOptionGroup {
  label: string
  order: number
  rows: CatalogModelRow[]
}

const CANVAS_MODEL_NODE_TYPES = ['chat', 'text', 'image', 'audio', 'video'] as const

const aiModelsCatalog = ref<{ models: CatalogModelRow[] } | null>(null)

function catalogRowVisibleOnCanvasNode(row: CatalogModelRow, nodeType: string): boolean {
  if (row.show_in_canvas_llm_nodes === false) return false
  if (row.canvas_universal) return true
  const kinds = row.canvas_node_kinds
  if (!kinds || kinds.length === 0) return true
  return kinds.includes(nodeType)
}

function buildModelOptionGroups(rows: CatalogModelRow[]): ModelOptionGroup[] {
  const map = new Map<string, ModelOptionGroup>()
  for (const row of rows) {
    const cid = String(row.category ?? 'other')
    const lab = row.category_label || '其它'
    const key = `${cid}@@${lab}`
    const order = typeof row.category_order === 'number' ? row.category_order : 999
    const g = map.get(key)
    if (g) g.rows.push(row)
    else map.set(key, { label: lab, order, rows: [row] })
  }
  return [...map.values()].sort((a, b) => a.order - b.order || a.label.localeCompare(b.label))
}

/** 当前选中节点类型下可见的模型分组（智能路由全节点；其余按 canvas_node_kinds） */
const modelOptionGroupsForInspector = computed<ModelOptionGroup[]>(() => {
  const nt = editorStore.selectedNode?.type ?? ''
  const all = aiModelsCatalog.value?.models ?? []
  const rows =
    CANVAS_MODEL_NODE_TYPES.includes(nt as (typeof CANVAS_MODEL_NODE_TYPES)[number])
      ? all.filter((row) => catalogRowVisibleOnCanvasNode(row, nt))
      : all
  return buildModelOptionGroups(rows)
})

function inferModelKeyFromLegacy(c: Record<string, any>): string {
  const existing = String(c.modelKey ?? '').trim()
  if (existing) return existing
  const m = String(c.model ?? '').trim()
  const p = String(c.provider ?? 'doubao').toLowerCase()
  if (!m) {
    if (p === 'doubao' || p === 'ark' || p === 'volcengine' || p === 'byte') return 'doubao-default'
    if (p === 'openai') return 'openai-default'
    if (p === 'claude') return 'claude-default'
    if (p === 'ollama' || p === 'ollama_chat') return 'ollama-default'
    if (p === 'vectorengine') return 'vectorengine-default'
    return ''
  }
  if (m.startsWith('ep-')) return ''
  const openaiMap: Record<string, string> = {
    'gpt-4o': 'openai-gpt-4o',
    'gpt-4o-mini': 'openai-gpt-4o-mini',
    'gpt-4-turbo': 'openai-gpt-4-turbo',
    'gpt-3.5-turbo': 'openai-gpt-3-5-turbo',
  }
  return openaiMap[m] || ''
}

function onInspectorModelKeyChange() {
  const k = String(inspectorConfig.value.modelKey ?? '').trim()
  if (k) {
    delete inspectorConfig.value.provider
    delete inspectorConfig.value.model
  }
  updateNodeConfig()
}

async function loadAiModelsCatalog() {
  try {
    const { data } = await api.get<{ models: CatalogModelRow[] }>('/ai/models')
    aiModelsCatalog.value = data
  } catch {
    aiModelsCatalog.value = null
  }
}

watch(
  () => editorStore.selectedNode,
  (node) => {
    if (node) {
      inspectorLabel.value = node.label
      const c = { ...(node.config || {}) } as Record<string, any>
      if (c.model == null || c.model === undefined) c.model = ''
      let mk = String(c.modelKey ?? '').trim()
      if (!mk) {
        const inferred = inferModelKeyFromLegacy(c)
        if (inferred) mk = inferred
      }
      inspectorConfig.value = { ...c, modelKey: mk }
    }
  }
)

/** 切换节点类型或目录加载后：当前 modelKey 若不在该节点可选列表中，回退到智能路由或列表首项 */
watch(modelOptionGroupsForInspector, (groups) => {
  const node = editorStore.selectedNode
  if (!node || !CANVAS_MODEL_NODE_TYPES.includes(node.type as (typeof CANVAS_MODEL_NODE_TYPES)[number])) return
  const allowed = new Set(groups.flatMap((g) => g.rows.map((r) => r.key)))
  const mk = String(inspectorConfig.value.modelKey ?? '').trim()
  if (mk && !allowed.has(mk)) {
    const rows = groups.flatMap((g) => g.rows)
    const fb = rows.find((r) => r.canvas_universal)?.key ?? rows[0]?.key ?? ''
    if (fb) {
      inspectorConfig.value.modelKey = fb
      updateNodeConfig()
    }
  }
})

// ── Icon resolution ───────────────────────────────────────────────────────────

const iconMap: Record<string, any> = {
  ChatDotRound,
  Tools,
  Connection: ConnectionIcon,
  CircleCheck,
  CopyDocument: CopyDocumentIcon,
  VideoPlay,
  Edit,
  Document,
  PictureFilled,
  Microphone,
  VideoCamera,
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

/** 调用 POST /workflows/canvas-node/run，client_node_id 与当前节点 id 对齐。 */
async function handleRunSelectedNode() {
  const wid = props.workflowId
  if (!wid) {
    ElMessage.warning('请先保存工作流后再调试节点')
    return
  }
  const node = editorStore.selectedNode
  if (!node) return
  try {
    const inputs: Record<string, unknown> = {}

    if (node.type === 'image') {
      const { value: urlVal } = await ElMessageBox.prompt(
        '输入图片 URL（可选；留空则仅按文本描述/提问执行）',
        '调试图片节点',
        {
          confirmButtonText: '下一步',
          cancelButtonText: '取消',
          inputPlaceholder: 'https://example.com/image.png',
          inputValue: String((node.config as any)?.image_url ?? ''),
        }
      )
      const imageUrl = String(urlVal ?? '').trim()
      if (imageUrl) inputs.image_url = imageUrl

      const { value: qVal } = await ElMessageBox.prompt(
        '输入对图片的提问/描述（对应 inputs.text）',
        '调试图片节点',
        {
          confirmButtonText: '运行',
          cancelButtonText: '取消',
          inputPlaceholder: '例如：这张图里有什么？',
          inputValue: '',
          inputValidator: (v) =>
            v != null && String(v).trim().length > 0 ? true : '请输入非空内容',
        }
      )
      inputs.text = String(qVal ?? '').trim()
    } else if (node.type === 'audio') {
      const { value } = await ElMessageBox.prompt(
        '输入音频转写文本（对应 inputs.transcript；本节点不做 ASR）',
        '调试音频节点',
        {
          confirmButtonText: '运行',
          cancelButtonText: '取消',
          inputPlaceholder: '例如：会议转写内容…',
          inputValue: '',
          inputValidator: (v) =>
            v != null && String(v).trim().length > 0 ? true : '请输入非空内容',
        }
      )
      inputs.transcript = String(value ?? '').trim()
      const audioUrl = String((node.config as any)?.audio_url ?? '').trim()
      if (audioUrl) inputs.audio_url = audioUrl
    } else if (node.type === 'video') {
      const { value } = await ElMessageBox.prompt(
        '输入视频相关文案/分镜说明（对应 inputs.description）',
        '调试视频节点',
        {
          confirmButtonText: '运行',
          cancelButtonText: '取消',
          inputPlaceholder: '例如：这是一个30秒产品介绍口播稿…',
          inputValue: '',
          inputValidator: (v) =>
            v != null && String(v).trim().length > 0 ? true : '请输入非空内容',
        }
      )
      inputs.description = String(value ?? '').trim()
      const videoUrl = String((node.config as any)?.video_url ?? '').trim()
      if (videoUrl) inputs.video_url = videoUrl
    } else if (node.type === 'text') {
      const { value } = await ElMessageBox.prompt(
        '输入要处理的文本（对应 inputs.text）',
        '调试文本节点',
        {
          confirmButtonText: '运行',
          cancelButtonText: '取消',
          inputPlaceholder: '例如：一段需要摘要/改写的文本…',
          inputValue: '',
          inputValidator: (v) =>
            v != null && String(v).trim().length > 0 ? true : '请输入非空内容',
        }
      )
      inputs.text = String(value ?? '').trim()
    } else {
      const { value } = await ElMessageBox.prompt(
        '输入传给该节点的用户文本（作为 inputs.text，与后端 AI 对话节点一致）',
        '调试运行节点',
        {
          confirmButtonText: '运行',
          cancelButtonText: '取消',
          inputPlaceholder: '例如：用一句话介绍你自己',
          inputValue: '',
          inputValidator: (v) =>
            v != null && String(v).trim().length > 0 ? true : '请输入非空内容',
        }
      )
      inputs.text = String(value ?? '').trim()
    }

    const res = await api.post<{
      execution_id: number
      status: string
      output: Record<string, unknown>
      error: string | null
    }>('/workflows/canvas-node/run', {
      workflow_id: wid,
      client_node_id: node.id,
      node_type: node.type,
      config: { ...node.config },
      inputs,
    })
    const data = res.data
    if (data.error) {
      ElMessage.error(data.error)
      return
    }
    const out = data.output
    const preview =
      typeof out?.text === 'string'
        ? out.text.slice(0, 800)
        : JSON.stringify(out ?? {}).slice(0, 800)
    ElMessage.success({
      message: preview || `状态: ${data.status}`,
      duration: 10000,
      showClose: true,
    })
  } catch (e: unknown) {
    if (e === 'cancel') return
    const err = e as { response?: { data?: { detail?: string } }; message?: string }
    ElMessage.error(err?.response?.data?.detail ?? err?.message ?? '请求失败')
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

function openEnhance(field: string) {
  enhanceField.value = field
  enhanceInitialValue.value = String((inspectorConfig.value as any)?.[field] ?? '')
  enhanceOpen.value = true
}

function applyEnhanced(v: string) {
  ;(inspectorConfig.value as any)[enhanceField.value] = v
  updateNodeConfig()
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

async function handleRunCanvas() {
  const wid = props.workflowId
  if (!wid) return
  // Entry: choose first node with no incoming edges, or fallback to first node
  const nodes = editorStore.nodes
  const edges = editorStore.edges
  const hasIncoming = new Set(edges.map((e) => e.targetNodeId))
  const entry = nodes.find((n) => !hasIncoming.has(n.id)) ?? nodes[0]
  if (!entry) return

  try {
    // Seed with a minimal text input if empty; user can refine later
    const initial_inputs: Record<string, any> = {}
    if (entry.type === 'chat' || entry.type === 'text') {
      initial_inputs.text = '你好'
    }
    const seedText =
      typeof initial_inputs.text === 'string' && initial_inputs.text.trim()
        ? initial_inputs.text.trim()
        : '你好'
    await workflowStore.startCanvasWorkflow({
      workflow_id: wid,
      query: seedText,
      entry_node_id: entry.id,
      initial_inputs,
    })
    ElMessage.success('已启动画布执行（请查看运行面板/监控）')
  } catch {
    // errors handled by store global interceptor
  }
}

// ── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(() => {
  void loadAiModelsCatalog()
  // 初次挂载时先按当前 props 初始化；后续编辑页会异步拉取 definition，需要 watch 才能回填
  if (props.initialDefinition && props.initialDefinition.nodes) {
    editorStore.loadFromDefinition(props.initialDefinition)
  } else {
    editorStore.clear()
  }
  canvasContainerRef.value?.focus()
})

watch(
  () => props.initialDefinition,
  (def) => {
    if (def && (def as any).nodes) {
      editorStore.loadFromDefinition(def as any)
    }
  },
  { deep: true }
)

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

.field-tools {
  display: flex;
  justify-content: flex-end;
  margin-top: -2px;
  margin-bottom: 6px;
}

.field-hint {
  margin-top: 4px;
  font-size: 11px;
  color: #999999;
}

.model-opt-title {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.3;
}

.model-own-key {
  margin-left: 6px;
  font-size: 11px;
  font-weight: 500;
  color: #409eff;
}

.model-opt-desc {
  font-size: 12px;
  color: #666666;
  line-height: 1.45;
  margin-top: 2px;
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
  max-width: 100%;
}

.inspector-video-hint {
  margin: 8px 0 0;
  font-size: 11px;
  line-height: 1.5;
  color: #888888;
}

.model-opt-tags {
  margin-top: 4px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.model-opt-tag {
  font-size: 10px;
  padding: 0 6px;
  border-radius: 3px;
  background: #f0f0f0;
  color: #555555;
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

<style lang="scss">
/* 模型下拉 teleport 到 body，scoped 无法命中；加宽选项避免中文说明被挤压成「方块」 */
.wf-model-catalog-popper {
  min-width: 300px !important;
  max-width: min(520px, 94vw);
}

.wf-model-catalog-popper .el-select-dropdown__item {
  height: auto !important;
  min-height: 44px;
  line-height: 1.45 !important;
  padding-top: 8px;
  padding-bottom: 8px;
  white-space: normal !important;
}
</style>
