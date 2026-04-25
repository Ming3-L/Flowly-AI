"""
AI Engine URL configuration.

All routes are mounted under /api/ via the project-level urls.py.
"""

from ninja import NinjaAPI  # pyright: ignore[reportMissingImports]

from .api import router as workflows_router, legacy_router
from .workflows import workflow_crud_router
from .executions import exec_router
from .rag_api import router as rag_router
from .task_api import router as task_router
from .analytics_api import router as analytics_router
from .custom_node_types import custom_node_type_router
from .prompt_tools_api import ai_router, prompt_tools_router
from .chat_sessions_api import chat_sessions_router
from .auto_reply_api import auto_reply_router
from .media_api import media_router
from .admin_portal_api import admin_router
from .ui_labels_api import router as ui_labels_router
from accounts.views import router as accounts_router
from accounts.api import router as profile_router
from accounts.social_views import router as social_router

api = NinjaAPI(
    title="Flowly AI API",
    description="AI-powered workflow engine API",
    version="1.0.0",
)

# /api/workflows/* — execution run, state, resume
api.add_router("/workflows", workflows_router)

# /api/workflows/* — CRUD operations
api.add_router("/workflows", workflow_crud_router)

# /api/executions/* — history, stats
api.add_router("/executions", exec_router)

# /api/ui-labels/* — 前端界面文案（公开读取，后台 Admin 维护）
api.add_router("/ui-labels", ui_labels_router)

# /api/auth/* — JWT auth, register, profile
api.add_router("/auth", accounts_router)
api.add_router("/auth", profile_router)
api.add_router("/auth", social_router)

# /api/documents/* — RAG knowledge base (Phase 8)
api.add_router("/documents", rag_router)

# /api/tasks/* — Celery async task management (Phase 9)
api.add_router("/tasks", task_router)

# /api/analytics/* — Usage, cost, and performance analytics (Phase 10)
api.add_router("/analytics", analytics_router)

# /api/custom-node-types/* — 用户自定义画布节点类型（ut_<id>）
api.add_router("/custom-node-types", custom_node_type_router)

# /api/ai/* — legacy execute/status endpoints + model catalog
api.add_router("/ai", legacy_router)

# /api/ai/models
api.add_router("/ai", ai_router)

# /api/prompt-tools/*
api.add_router("/prompt-tools", prompt_tools_router)

# /api/chat/* — 独立 AI 对话会话（列表 / 新建 / 删除 / 消息）
api.add_router("/chat", chat_sessions_router)

# /api/auto-reply/* — AI 自动回复规则与异步任务
api.add_router("/auto-reply", auto_reply_router)

# /api/media/* — 上传与受保护下载（工作流多模态输入）
api.add_router("/media", media_router)

# /api/admin/* — 平台后台管理（仅管理员）
api.add_router("/admin", admin_router)
