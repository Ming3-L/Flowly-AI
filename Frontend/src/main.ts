import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './styles/main.scss'
import { useUiLabelsStore } from './stores/uiLabels'

async function bootstrap() {
  const app = createApp(App)

  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }

  const pinia = createPinia()
  app.use(pinia)
  app.use(router)
  app.use(ElementPlus)

  const ui = useUiLabelsStore(pinia)
  try {
    await Promise.race([
      ui.fetchLabels('zh-CN'),
      new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error('ui-labels-timeout')), 10000)
      }),
    ])
  } catch {
    // 超时或网络失败：仍挂载应用，文案回退为键名；生产环境应保证 /api/ui-labels 可用
  }

  app.mount('#app')
}

bootstrap()
