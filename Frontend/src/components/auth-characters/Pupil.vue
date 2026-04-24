<template>
  <div
    ref="pupilRef"
    class="ac-pupil-root"
    :style="{
      width: `${size}px`,
      height: `${size}px`,
      backgroundColor: pupilColor,
      transform: `translate(${pos.x}px, ${pos.y}px)`,
      transition: 'transform 0.1s ease-out',
    }"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    size?: number
    maxDistance?: number
    pupilColor?: string
    forceLookX?: number
    forceLookY?: number
    mouseX: number
    mouseY: number
  }>(),
  {
    size: 12,
    maxDistance: 5,
    pupilColor: '#2D2D2D',
  },
)

const pupilRef = ref<HTMLElement | null>(null)

const pos = computed(() => {
  if (props.forceLookX !== undefined && props.forceLookY !== undefined) {
    return { x: props.forceLookX, y: props.forceLookY }
  }
  const el = pupilRef.value
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
.ac-pupil-root {
  border-radius: 50%;
}
</style>
