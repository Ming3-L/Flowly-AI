<template>
  <g class="styled-edge" :class="{ selected, animated }">
    <!-- Shadow / glow when selected -->
    <defs>
      <filter id="edge-glow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="3" result="coloredBlur" />
        <feMerge>
          <feMergeNode in="coloredBlur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>

    <!-- Invisible wider path for click target -->
    <path
      :d="path"
      fill="none"
      stroke="transparent"
      stroke-width="12"
      class="edge-hit-area"
      @click="onEdgeClick"
    />

    <!-- Visible path -->
    <path
      :d="path"
      fill="none"
      :stroke="selected ? '#000000' : '#b3b3b3'"
      :stroke-width="selected ? 2.5 : 2"
      :stroke-dasharray="animated ? '5,5' : undefined"
      :stroke-dashoffset="animated ? 0 : undefined"
      :marker-end="selected ? 'url(#arrowhead-selected)' : 'url(#arrowhead)'"
      :filter="selected ? 'url(#edge-glow)' : undefined"
      class="edge-path"
    />

    <!-- Label -->
    <g v-if="label" class="edge-label" @click="onEdgeClick">
      <rect
        :x="labelX - labelWidth / 2"
        :y="labelY - 10"
        :width="labelWidth"
        :height="20"
        rx="4"
        fill="#ffffff"
        stroke="#e0e0e0"
        stroke-width="1"
      />
      <text :x="labelX" :y="labelY + 4" text-anchor="middle" font-size="11" fill="#333333">
        {{ label }}
      </text>
    </g>

    <!-- Delete button when selected -->
    <g v-if="selected" class="edge-delete" @click.stop="onDeleteClick">
      <circle :cx="midX" :cy="midY" r="8" fill="#000000" stroke="#ffffff" stroke-width="1.5" />
      <line
        :x1="midX - 4"
        :y1="midY - 4"
        :x2="midX + 4"
        :y2="midY + 4"
        stroke="#fff"
        stroke-width="1.5"
        stroke-linecap="round"
      />
      <line
        :x1="midX + 4"
        :y1="midY - 4"
        :x2="midX - 4"
        :y2="midY + 4"
        stroke="#fff"
        stroke-width="1.5"
        stroke-linecap="round"
      />
    </g>
  </g>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getBezierPath } from '@vue-flow/core'

interface Props {
  id: string
  sourceX: number
  sourceY: number
  targetX: number
  targetY: number
  sourcePosition: any
  targetPosition: any
  sourceHandleId?: string | null
  targetHandleId?: string | null
  label?: string
  animated?: boolean
  selected?: boolean
  markerEnd?: string
}

const props = withDefaults(defineProps<Props>(), {
  sourceHandleId: null,
  targetHandleId: null,
  label: undefined,
  animated: false,
  selected: false,
})

const emit = defineEmits<{
  click: [id: string]
  delete: [id: string]
}>()

const pathData = computed(() => {
  const result = getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    targetX: props.targetX,
    targetY: props.targetY,
    sourcePosition: props.sourcePosition,
    targetPosition: props.targetPosition,
  })
  return result[0]
})

const path = computed(() => pathData.value)

const midX = computed(() => (props.sourceX + props.targetX) / 2)
const midY = computed(() => (props.sourceY + props.targetY) / 2)

const labelWidth = computed(() => {
  const len = (props.label ?? '').length
  return Math.max(40, len * 7 + 12)
})
const labelX = computed(() => midX.value)
const labelY = computed(() => midY.value - 14)

function onEdgeClick() {
  emit('click', props.id)
}

function onDeleteClick() {
  emit('delete', props.id)
}
</script>

<style scoped lang="scss">
.styled-edge {
  cursor: pointer;
}

.edge-path {
  transition: stroke 0.15s, stroke-width 0.15s;
}

.edge-hit-area {
  cursor: pointer;
}

.edge-label {
  cursor: pointer;

  rect {
    transition: fill 0.15s;
  }

  &:hover rect {
    fill: #f5f5f5;
  }
}

.edge-delete {
  cursor: pointer;
  transition: opacity 0.15s;

  circle {
    transition: r 0.15s, fill 0.15s;
  }

  &:hover circle {
    r: 10;
    fill: #333333;
  }
}

.animated .edge-path {
  animation: dash 0.5s linear infinite;
}

@keyframes dash {
  from {
    stroke-dashoffset: 10;
  }
  to {
    stroke-dashoffset: 0;
  }
}
</style>
