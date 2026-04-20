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
from accounts.views import router as accounts_router
from accounts.api import router as profile_router

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

# /api/auth/* — JWT auth, register, profile
api.add_router("/auth", accounts_router)
api.add_router("/auth", profile_router)

# /api/documents/* — RAG knowledge base (Phase 8)
api.add_router("/documents", rag_router)

# /api/tasks/* — Celery async task management (Phase 9)
api.add_router("/tasks", task_router)

# /api/analytics/* — Usage, cost, and performance analytics (Phase 10)
api.add_router("/analytics", analytics_router)

# /api/ai/* — legacy execute/status endpoints
api.add_router("/ai", legacy_router)
