"""
URL configuration for flowly_backend project.
"""

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.http import JsonResponse
from django.db import connection

from ai_engine.urls import api

def health_check(request):
    """
    GET /health/ — liveness probe.

    注意：Railway 的 healthcheck 失败会导致整个服务被标记为不可用（Edge 直接返回 502/fallback），
    因此这里**不**依赖数据库连接，只用于确认进程存活与路由可达。
    """
    return JsonResponse({"status": "ok"})


def ready_check(request):
    """GET /ready/ — readiness probe（依赖数据库）。"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ready", "database": "ok"})
    except Exception as exc:
        return JsonResponse(
            {"status": "not_ready", "database": "error", "detail": str(exc)},
            status=503,
        )

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("health/", health_check, name="health_check"),
    path("ready/", ready_check, name="ready_check"),
]

# 开发环境：提供 MEDIA_URL 静态访问（生产建议由 Nginx/对象存储提供）
if getattr(settings, "DEBUG", False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
