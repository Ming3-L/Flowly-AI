import { ref } from 'vue'

// Plain shared ref — avoids Pinia initialization order issues.
// Both App.vue and Home.vue import this for isDarkTheme reactivity.
export const themeVersion = ref(0)

export function incrementThemeVersion() {
  themeVersion.value++
}
