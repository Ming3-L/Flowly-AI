/// <reference types="vite/client" />

declare global {
  interface Window {
    __FLOWLY_RUNTIME__?: {
      /** e.g. "https://your-backend.up.railway.app/api" */
      API_BASE_URL?: string
    }
  }
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  const component: DefineComponent<object, object, any>
  export default component
}
