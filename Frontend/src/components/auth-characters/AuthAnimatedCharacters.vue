<template>
  <div class="ac-scale-wrap" style="left: 5px; top: 67px;">
    <div class="ac-stage" aria-hidden="true" ref="stageRef">
      <!-- Purple -->
      <div
        ref="purpleRef"
        class="ac-char ac-purple"
        :style="{
          left: '116px',
          width: '180px',
          height: purpleHeight,
          backgroundColor: '#6C3FF5',
          borderRadius: '10px 10px 0 0',
          zIndex: 1,
          transform: purpleTransform,
          transformOrigin: 'bottom center',
          top: '-256px',
        }"
      >
        <div
          class="ac-eyes ac-eyes-row"
          :style="{
            left: purpleEyeLeft,
            top: purpleEyeTop,
          }"
        >
          <EyeBall
            :size="18"
            :pupil-size="7"
            :max-distance="5"
            eye-color="white"
            pupil-color="#2D2D2D"
            :is-blinking="isPurpleBlinking"
            :force-look-x="purpleForceX"
            :force-look-y="purpleForceY"
            :mouse-x="mouseX"
            :mouse-y="mouseY"
          />
          <EyeBall
            :size="18"
            :pupil-size="7"
            :max-distance="5"
            eye-color="white"
            pupil-color="#2D2D2D"
            :is-blinking="isPurpleBlinking"
            :force-look-x="purpleForceX"
            :force-look-y="purpleForceY"
            :mouse-x="mouseX"
            :mouse-y="mouseY"
          />
        </div>
      </div>

      <!-- Black -->
      <div
        ref="blackRef"
        class="ac-char ac-black"
        :style="{
          left: '242px',
          width: '120px',
          height: '310px',
          backgroundColor: '#2D2D2D',
          borderRadius: '8px 8px 0 0',
          zIndex: 2,
          transform: blackTransform,
          transformOrigin: 'bottom center',
          top: '-167px',
        }"
      >
        <div
          class="ac-eyes ac-eyes-row ac-eyes-tight"
          :style="{
            left: blackEyeLeft,
            top: blackEyeTop,
          }"
        >
          <EyeBall
            :size="16"
            :pupil-size="6"
            :max-distance="4"
            eye-color="white"
            pupil-color="#2D2D2D"
            :is-blinking="isBlackBlinking"
            :force-look-x="blackForceX"
            :force-look-y="blackForceY"
            :mouse-x="mouseX"
            :mouse-y="mouseY"
          />
          <EyeBall
            :size="16"
            :pupil-size="6"
            :max-distance="4"
            eye-color="white"
            pupil-color="#2D2D2D"
            :is-blinking="isBlackBlinking"
            :force-look-x="blackForceX"
            :force-look-y="blackForceY"
            :mouse-x="mouseX"
            :mouse-y="mouseY"
          />
        </div>
      </div>

      <!-- Orange -->
      <div
        ref="orangeRef"
        class="ac-char ac-orange"
        :style="{
          left: '19px',
          width: '240px',
          height: '200px',
          zIndex: 3,
          backgroundColor: '#FF9B6B',
          borderRadius: '120px 120px 0 0',
          transform: orangeTransform,
          transformOrigin: 'bottom center',
          top: '-56px',
        }"
      >
        <div
          class="ac-eyes ac-eyes-row"
          :style="{
            left: orangePupilLeft,
            top: orangePupilTop,
          }"
        >
          <Pupil
            :size="12"
            :max-distance="5"
            pupil-color="#2D2D2D"
            :force-look-x="orangeForceX"
            :force-look-y="orangeForceY"
            :mouse-x="mouseX"
            :mouse-y="mouseY"
          />
          <Pupil
            :size="12"
            :max-distance="5"
            pupil-color="#2D2D2D"
            :force-look-x="orangeForceX"
            :force-look-y="orangeForceY"
            :mouse-x="mouseX"
            :mouse-y="mouseY"
          />
        </div>
      </div>

      <!-- Yellow -->
      <div
        ref="yellowRef"
        class="ac-char ac-yellow"
        :style="{
          left: '327px',
          width: '140px',
          height: '230px',
          backgroundColor: '#E8D754',
          borderRadius: '70px 70px 0 0',
          zIndex: 4,
          transform: yellowTransform,
          transformOrigin: 'bottom center',
          top: '-84px',
        }"
      >
        <div
          class="ac-eyes ac-eyes-row ac-eyes-tight"
          :style="{
            left: yellowPupilLeft,
            top: yellowPupilTop,
          }"
        >
          <Pupil
            :size="12"
            :max-distance="5"
            pupil-color="#2D2D2D"
            :force-look-x="yellowForceX"
            :force-look-y="yellowForceY"
            :mouse-x="mouseX"
            :mouse-y="mouseY"
          />
          <Pupil
            :size="12"
            :max-distance="5"
            pupil-color="#2D2D2D"
            :force-look-x="yellowForceX"
            :force-look-y="yellowForceY"
            :mouse-x="mouseX"
            :mouse-y="mouseY"
          />
        </div>
        <div
          class="ac-mouth"
          :style="{
            left: yellowMouthLeft,
            top: yellowMouthTop,
          }"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import type { Ref } from 'vue'
import EyeBall from './EyeBall.vue'
import Pupil from './Pupil.vue'

const props = withDefaults(
  defineProps<{
    isTyping?: boolean
    showPassword?: boolean
    passwordLength?: number
  }>(),
  {
    isTyping: false,
    showPassword: false,
    passwordLength: 0,
  },
)

const mouseX = ref(0)
const mouseY = ref(0)
const purpleRef = ref<HTMLElement | null>(null)
const blackRef = ref<HTMLElement | null>(null)
const yellowRef = ref<HTMLElement | null>(null)
const orangeRef = ref<HTMLElement | null>(null)
const stageRef = ref<HTMLElement | null>(null)

const isPurpleBlinking = ref(false)
const isBlackBlinking = ref(false)
const isLookingAtEachOther = ref(false)
const isPurplePeeking = ref(false)

const stageWidth = ref(520)

onMounted(() => {
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('resize', updateStageWidth)
  schedulePurpleBlink()
  scheduleBlackBlink()
  updateStageWidth()
})

function updateStageWidth() {
  if (stageRef.value) {
    stageWidth.value = stageRef.value.offsetWidth
  }
}

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('resize', updateStageWidth)
  if (purpleBlinkTimer) clearTimeout(purpleBlinkTimer)
  if (blackBlinkTimer) clearTimeout(blackBlinkTimer)
  if (lookTimer) clearTimeout(lookTimer)
  clearPeekChain()
})

function calculatePosition(elRef: Ref<HTMLElement | null>) {
  const el = elRef.value
  if (!el) return { faceX: 0, faceY: 0, bodySkew: 0 }
  const rect = el.getBoundingClientRect()
  const centerX = rect.left + rect.width / 2
  const centerY = rect.top + rect.height / 3
  const deltaX = mouseX.value - centerX
  const deltaY = mouseY.value - centerY
  const faceX = Math.max(-15, Math.min(15, deltaX / 20))
  const faceY = Math.max(-10, Math.min(10, deltaY / 30))
  const bodySkew = Math.max(-6, Math.min(6, -deltaX / 120))
  return { faceX, faceY, bodySkew }
}

const purplePos = computed(() => calculatePosition(purpleRef))
const blackPos = computed(() => calculatePosition(blackRef))
const yellowPos = computed(() => calculatePosition(yellowRef))
const orangePos = computed(() => calculatePosition(orangeRef))

const isHidingPassword = computed(() => props.passwordLength > 0 && !props.showPassword)

const purpleHeight = computed(() =>
  props.isTyping || isHidingPassword.value ? '440px' : '400px',
)

const purpleTransform = computed(() => {
  if (props.passwordLength > 0 && props.showPassword) {
    return 'skewX(0deg)'
  }
  if (props.isTyping || isHidingPassword.value) {
    return `skewX(${(purplePos.value.bodySkew || 0) - 12}deg) translateX(40px)`
  }
  return `skewX(${purplePos.value.bodySkew || 0}deg)`
})

const blackTransform = computed(() => {
  if (props.passwordLength > 0 && props.showPassword) {
    return 'skewX(0deg)'
  }
  if (isLookingAtEachOther.value) {
    return `skewX(${(blackPos.value.bodySkew || 0) * 1.5 + 10}deg) translateX(20px)`
  }
  if (props.isTyping || isHidingPassword.value) {
    return `skewX(${(blackPos.value.bodySkew || 0) * 1.5}deg)`
  }
  return `skewX(${blackPos.value.bodySkew || 0}deg)`
})

const orangeTransform = computed(() => {
  if (props.passwordLength > 0 && props.showPassword) {
    return 'skewX(0deg)'
  }
  return `skewX(${orangePos.value.bodySkew || 0}deg)`
})

const yellowTransform = computed(() => {
  if (props.passwordLength > 0 && props.showPassword) {
    return 'skewX(0deg)'
  }
  return `skewX(${yellowPos.value.bodySkew || 0}deg)`
})

const pwdReveal = computed(() => props.passwordLength > 0 && props.showPassword)

const purpleEyeLeft = computed(() => {
  if (pwdReveal.value) return '20px'
  if (isLookingAtEachOther.value) return '55px'
  return `${45 + purplePos.value.faceX}px`
})

const purpleEyeTop = computed(() => {
  if (pwdReveal.value) return '35px'
  if (isLookingAtEachOther.value) return '65px'
  return `${40 + purplePos.value.faceY}px`
})

const purpleForceX = computed(() => {
  if (!pwdReveal.value) {
    if (isLookingAtEachOther.value) return 3
    return undefined
  }
  return isPurplePeeking.value ? 4 : -4
})

const purpleForceY = computed(() => {
  if (!pwdReveal.value) {
    if (isLookingAtEachOther.value) return 4
    return undefined
  }
  return isPurplePeeking.value ? 5 : -4
})

const blackEyeLeft = computed(() => {
  if (pwdReveal.value) return '10px'
  if (isLookingAtEachOther.value) return '32px'
  return `${26 + blackPos.value.faceX}px`
})

const blackEyeTop = computed(() => {
  if (pwdReveal.value) return '28px'
  if (isLookingAtEachOther.value) return '12px'
  return `${32 + blackPos.value.faceY}px`
})

const blackForceX = computed(() => {
  if (pwdReveal.value) return -4
  if (isLookingAtEachOther.value) return 0
  return undefined
})

const blackForceY = computed(() => {
  if (pwdReveal.value) return -4
  if (isLookingAtEachOther.value) return -4
  return undefined
})

const orangePupilLeft = computed(() => {
  if (pwdReveal.value) return '50px'
  return `${82 + (orangePos.value.faceX || 0)}px`
})

const orangePupilTop = computed(() => {
  if (pwdReveal.value) return '85px'
  return `${90 + (orangePos.value.faceY || 0)}px`
})

const orangeForceX = computed(() => (pwdReveal.value ? -5 : undefined))
const orangeForceY = computed(() => (pwdReveal.value ? -4 : undefined))

const yellowPupilLeft = computed(() => {
  if (pwdReveal.value) return '20px'
  return `${52 + (yellowPos.value.faceX || 0)}px`
})

const yellowPupilTop = computed(() => {
  if (pwdReveal.value) return '35px'
  return `${40 + (yellowPos.value.faceY || 0)}px`
})

const yellowForceX = computed(() => (pwdReveal.value ? -5 : undefined))
const yellowForceY = computed(() => (pwdReveal.value ? -4 : undefined))

const yellowMouthLeft = computed(() => {
  if (pwdReveal.value) return '10px'
  return `${40 + (yellowPos.value.faceX || 0)}px`
})

const yellowMouthTop = computed(() => {
  if (pwdReveal.value) return '88px'
  return `${88 + (yellowPos.value.faceY || 0)}px`
})

function onMouseMove(e: MouseEvent) {
  mouseX.value = e.clientX
  mouseY.value = e.clientY
}

let purpleBlinkTimer: number | null = null
let blackBlinkTimer: number | null = null
let lookTimer: number | null = null
let peekOuter: number | null = null
let peekInner: number | null = null

function schedulePurpleBlink() {
  const delay = Math.random() * 4000 + 3000
  purpleBlinkTimer = window.setTimeout(() => {
    isPurpleBlinking.value = true
    window.setTimeout(() => {
      isPurpleBlinking.value = false
      schedulePurpleBlink()
    }, 150)
  }, delay)
}

function scheduleBlackBlink() {
  const delay = Math.random() * 4000 + 3000
  blackBlinkTimer = window.setTimeout(() => {
    isBlackBlinking.value = true
    window.setTimeout(() => {
      isBlackBlinking.value = false
      scheduleBlackBlink()
    }, 150)
  }, delay)
}

function clearPeekChain() {
  if (peekOuter) {
    clearTimeout(peekOuter)
    peekOuter = null
  }
  if (peekInner) {
    clearTimeout(peekInner)
    peekInner = null
  }
}

watch(
  () => props.isTyping,
  (v) => {
    if (lookTimer) clearTimeout(lookTimer)
    if (v) {
      isLookingAtEachOther.value = true
      lookTimer = window.setTimeout(() => {
        isLookingAtEachOther.value = false
      }, 800)
    } else {
      isLookingAtEachOther.value = false
    }
  },
)

watch(
  () => [props.passwordLength, props.showPassword] as const,
  ([len, show]) => {
    clearPeekChain()
    isPurplePeeking.value = false
    if (len <= 0 || !show) return
    const schedulePeek = () => {
      peekOuter = window.setTimeout(() => {
        isPurplePeeking.value = true
        peekInner = window.setTimeout(() => {
          isPurplePeeking.value = false
          schedulePeek()
        }, 800)
      }, 2000 + Math.random() * 3000)
    }
    schedulePeek()
  },
  { immediate: true },
)
</script>

<style scoped lang="scss">
.ac-scale-wrap {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.ac-stage {
  position: absolute;
  left: 50%;
  transform: translateX(-50%) scale(0.68);
  transform-origin: center center;
  width: 520px;
}

.ac-char {
  position: absolute;
  top: 0;
  transition: transform 0.7s ease-in-out, height 0.7s ease-in-out;
}

.ac-eyes {
  position: absolute;
  display: flex;
  transition: left 0.7s ease-in-out, top 0.7s ease-in-out;
}

.ac-eyes-row {
  gap: 32px;
}

.ac-eyes-tight {
  gap: 24px;
}

.ac-mouth {
  position: absolute;
  width: 80px;
  height: 4px;
  background: #2d2d2d;
  border-radius: 999px;
  transition: left 0.2s ease-out, top 0.2s ease-out;
}

// ── Stats Dashboard Panel ─────────────────────────────────────────────────────
.ac-stats-panel {
  width: 100%;
  max-width: 360px;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.13);
  border-radius: 14px;
  padding: 14px 18px;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow:
    0 4px 24px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.ac-stats-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
}

.ac-stats-live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.6);
  animation: pulse-green 2s ease-in-out infinite;
  flex-shrink: 0;
}

@keyframes pulse-green {
  0%, 100% { opacity: 1; box-shadow: 0 0 6px rgba(34, 197, 94, 0.6); }
  50% { opacity: 0.6; box-shadow: 0 0 2px rgba(34, 197, 94, 0.3); }
}

.ac-stats-live-label {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.ac-stats-grid {
  display: flex;
  align-items: center;
  gap: 0;
  margin-bottom: 12px;
}

.ac-stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.ac-stat-divider {
  width: 1px;
  height: 32px;
  background: rgba(255, 255, 255, 0.1);
}

.ac-stat-value {
  font-size: 18px;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: -0.5px;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.35);
}

.ac-stat-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.45);
  font-weight: 500;
  letter-spacing: 0.2px;
  white-space: nowrap;
}

.ac-stats-footer {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

.ac-mini-chart {
  flex: 1;
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 28px;
}

.ac-chart-bar {
  flex: 1;
  background: linear-gradient(to top, #6C3FF5, #a78bfa);
  border-radius: 3px 3px 0 0;
  min-height: 4px;
  transition: height 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
  opacity: 0.75;
}

.ac-stats-update {
  font-size: 9px;
  color: rgba(255, 255, 255, 0.3);
  white-space: nowrap;
  font-weight: 400;
}

@media (prefers-reduced-motion: reduce) {
  .ac-char {
    transition: none;
  }
  .ac-eyes {
    transition: none;
  }
  .ac-mouth {
    transition: none;
  }
  .ac-chart-bar {
    transition: none;
  }
  .ac-stats-live-dot {
    animation: none;
  }
}
</style>
