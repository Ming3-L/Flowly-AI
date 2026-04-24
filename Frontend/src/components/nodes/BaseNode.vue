<template>
  <div class="base-node" :class="{ selected }">
    <!-- Color accent bar -->
    <div class="node-accent" :style="{ background: nodeColor }" />

    <!-- Header -->
    <div class="node-header">
      <span class="node-type-badge" :style="{ color: nodeColor }">{{ typeLabel }}</span>
      <el-icon class="node-drag-handle" :size="12" color="#909399"><MoreFilled /></el-icon>
    </div>

    <!-- Label -->
    <div class="node-label">{{ data.label }}</div>

    <!-- Config preview (optional, shown for some types) -->
    <div v-if="configPreview" class="node-config-preview">{{ configPreview }}</div>

    <!-- Handle: Left (target / in) -->
    <Handle id="in" type="target" :position="Position.Left" class="handle handle-left" />

    <!-- Handle: Right (source / out) -->
    <Handle
      v-if="!hasMultiSource"
      id="out"
      type="source"
      :position="Position.Right"
      class="handle handle-right"
    />

    <!-- Handle: Right-True (condition true branch) -->
    <Handle
      v-if="nodeType === 'condition'"
      id="true"
      type="source"
      :position="Position.Right"
      :style="{ top: '40%' }"
      class="handle handle-right"
    />

    <!-- Handle: Bottom-False (condition false branch) -->
    <Handle
      v-if="nodeType === 'condition'"
      id="false"
      type="source"
      :position="Position.Bottom"
      class="handle handle-bottom"
    />

    <!-- Handle: Right-Approved (human_approval) -->
    <Handle
      v-if="nodeType === 'human_approval'"
      id="approved"
      type="source"
      :position="Position.Right"
      :style="{ top: '40%' }"
      class="handle handle-right"
    />

    <!-- Handle: Bottom-Rejected (human_approval) -->
    <Handle
      v-if="nodeType === 'human_approval'"
      id="rejected"
      type="source"
      :position="Position.Bottom"
      class="handle handle-bottom"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { MoreFilled } from '@element-plus/icons-vue'
import { NODE_TYPE_META } from '@/types/workflow-editor'
import type { EditorNodeType } from '@/types/workflow-editor'

interface Props {
  id: string
  type: string
  data: {
    label: string
    config: Record<string, any>
    style?: { color?: string }
  }
  selected?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  selected: false,
})

const nodeType = computed(() => props.type as EditorNodeType)
const meta = computed(() => NODE_TYPE_META[nodeType.value])
const nodeColor = computed(() => props.data?.style?.color ?? meta.value?.color ?? '#000000')
const typeLabel = computed(() => meta.value?.label ?? props.type)
const hasMultiSource = computed(() => ['condition', 'human_approval'].includes(nodeType.value))

const configPreview = computed(() => {
  const cfg = props.data?.config ?? {}
  switch (nodeType.value) {
    case 'chat':
      return cfg.model ? `Model: ${cfg.model}` : null
    case 'tool':
      return cfg.toolName ? `Tool: ${cfg.toolName}` : null
    case 'condition':
      return cfg.conditionExpression ? cfg.conditionExpression.slice(0, 24) + '…' : null
    case 'human_approval':
      return cfg.approvalQuestion ? cfg.approvalQuestion.slice(0, 24) + '…' : null
    case 'text': {
      const p = String(cfg.prompt ?? '').trim()
      return p ? `Prompt: ${p.slice(0, 28)}${p.length > 28 ? '…' : ''}` : null
    }
    case 'image': {
      const url = String(cfg.image_url ?? '').trim()
      return url ? `Image: ${url.slice(0, 30)}${url.length > 30 ? '…' : ''}` : 'Image'
    }
    case 'audio': {
      const url = String(cfg.audio_url ?? '').trim()
      return url ? `Audio: ${url.slice(0, 30)}${url.length > 30 ? '…' : ''}` : 'Audio'
    }
    case 'video': {
      const url = String(cfg.video_url ?? '').trim()
      return url ? `Video: ${url.slice(0, 30)}${url.length > 30 ? '…' : ''}` : 'Video'
    }
    default:
      return null
  }
})
</script>

<style scoped lang="scss">
.base-node {
  position: relative;
  width: 200px;
  min-height: 72px;
  background: #ffffff;
  border: 2px solid v-bind(nodeColor);
  border-radius: 4px;
  box-shadow: 0px 1px 3px rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.15s, border-color 0.15s;

  &.selected {
    box-shadow: 0 0 0 2px v-bind(nodeColor);
    border-color: v-bind(nodeColor);
  }
}

.node-accent {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 3px 0 0 3px;
  background: v-bind(nodeColor);
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px 2px 14px;
}

.node-type-badge {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.node-drag-handle {
  cursor: grab;
  opacity: 0;
  transition: opacity 0.15s;

  &:active {
    cursor: grabbing;
  }
}

.base-node:hover .node-drag-handle {
  opacity: 1;
}

.node-label {
  padding: 0 10px 6px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #000000;
  line-height: 1.3;
  word-break: break-word;
}

.node-config-preview {
  padding: 0 10px 6px 14px;
  font-size: 10px;
  color: #666666;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

// ── Handles ─────────────────────────────────────────────────────────────────

.handle {
  width: 10px !important;
  height: 10px !important;
  background: #cccccc !important;
  border: 2px solid #ffffff !important;
  border-radius: 50% !important;
  transition: background 0.15s, transform 0.15s;

  &:hover {
    background: v-bind(nodeColor) !important;
    transform: scale(1.3);
  }
}

.handle-left {
  left: -6px !important;
}

.handle-right {
  right: -6px !important;
}

.handle-bottom {
  bottom: -6px !important;
  left: 50% !important;
  transform: translateX(-50%) !important;

  &:hover {
    transform: translateX(-50%) scale(1.3) !important;
  }
}
</style>
