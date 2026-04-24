<template>
  <div
    ref="eyeRef"
    class="ac-eye"
    :style="{
      width: `${size}px`,
      height: isBlinking ? '2px' : `${size}px`,
      backgroundColor: eyeColor,
      overflow: 'hidden',
    }"
  >
    <div
      v-if="!isBlinking"
      class="ac-eye-inner"
      :style="{
        width: `${pupilSize}px`,
        height: `${pupilSize}px`,
        backgroundColor: pupilColor,
        '--px': `${pupilPos.x}px`,
        '--py': `${pupilPos.y}px`,
      }"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    size?: number
    pupilSize?: number
    maxDistance?: number
    eyeColor?: string
    pupilColor?: string
    isBlinking?: boolean
    forceLookX?: number
    forceLookY?: number
    mouseX: number
    mouseY: number
  }>(),
  {
    size: 48,
    pupilSize: 16,
    maxDistance: 10,
    eyeColor: 'white',
    pupilColor: 'black',
    isBlinking: false,
  },
)

const eyeRef = ref<HTMLElement | null>(null)

const pupilPos = computed(() => {
  if (props.forceLookX !== undefined && props.forceLookY !== undefined) {
    return { x: props.forceLookX, y: props.forceLookY }
  }
  const el = eyeRef.value
  if (!el) return { x: 0, y: 0 }
  const rect = el.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2
  const dx = props.mouseX - cx
  const dy = props.mouseY - cy
  const dist = Math.min(Math.hypot(dx, dy), props.maxDistance)
  const angle = Math.atan2(dy, dx)
  return { x: Math.cos(angle) * dist, y: Math.sin(angle) * dist }
})
</script>

<style scoped>
.ac-eye {
  position: relative;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: height 0.15s ease;
}

.ac-eye-inner {
  position: absolute;
  left: 50%;
  top: 50%;
  border-radius: 999px;
  transform: translate(calc(-50% + var(--px, 0px)), calc(-50% + var(--py, 0px)));
  transition: transform 0.1s ease-out;
}
</style>
