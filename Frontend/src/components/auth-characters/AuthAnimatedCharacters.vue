<template>
  <div class="ac-scale-wrap">
    <div class="ac-stage" aria-hidden="true">
      <!-- Purple -->
      <div
        ref="purpleRef"
        class="ac-char ac-purple"
        :style="{
          left: '70px',
          width: '180px',
          height: purpleHeight,
          backgroundColor: '#6C3FF5',
          borderRadius: '10px 10px 0 0',
          zIndex: 1,
          transform: purpleTransform,
          transformOrigin: 'bottom center',
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
          left: '240px',
          width: '120px',
          height: '310px',
          backgroundColor: '#2D2D2D',
          borderRadius: '8px 8px 0 0',
          zIndex: 2,
          transform: blackTransform,
          transformOrigin: 'bottom center',
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
          left: '0px',
          width: '240px',
          height: '200px',
          zIndex: 3,
          backgroundColor: '#FF9B6B',
          borderRadius: '120px 120px 0 0',
          transform: orangeTransform,
          transformOrigin: 'bottom center',
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
          left: '310px',
          width: '140px',
          height: '230px',
          backgroundColor: '#E8D754',
          borderRadius: '70px 70px 0 0',
          zIndex: 4,
          transform: yellowTransform,
          transformOrigin: 'bottom center',
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

const isPurpleBlinking = ref(false)
const isBlackBlinking = ref(false)
const isLookingAtEachOther = ref(false)
const isPurplePeeking = ref(false)

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

onMounted(() => {
  window.addEventListener('mousemove', onMouseMove)
  schedulePurpleBlink()
  scheduleBlackBlink()
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  if (purpleBlinkTimer) clearTimeout(purpleBlinkTimer)
  if (blackBlinkTimer) clearTimeout(blackBlinkTimer)
  if (lookTimer) clearTimeout(lookTimer)
  clearPeekChain()
})

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
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 220px;
  /* 原 flex-end + bottom 锚点会让视觉重心贴底，在半透明白框里显偏下 */
  transform: translateY(-28px);

  @media (max-width: 520px) {
    transform: translateY(-18px);
  }
}

.ac-stage {
  position: relative;
  width: 550px;
  height: 400px;
  transform: scale(0.58);
  transform-origin: center 78%;

  @media (max-width: 520px) {
    transform: scale(0.42);
    transform-origin: center 78%;
  }
}

.ac-char {
  position: absolute;
  bottom: 0;
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
}
</style>
