// Runtime configuration (optional).
// Static hosting & Electron can overwrite this file at deploy-time to avoid rebuilding.
// Example:
// window.__FLOWLY_RUNTIME__ = { API_BASE_URL: "https://your-backend.up.railway.app/api" }



window.__FLOWLY_RUNTIME__ = {
    // 线上后端（优先级最高）
    API_BASE_URL: "https://flowly-ai-production-2ba5.up.railway.app/api",
    // 线上后端（优先级最高）
    API_BASE_URL_LOCAL: "http://localhost:8000/api"
}