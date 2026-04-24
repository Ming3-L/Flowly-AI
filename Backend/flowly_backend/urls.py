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
    """GET /health/ — Kubernetes/Docker health check endpoint."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({
            "status": "healthy",
            "database": "ok",
        })
    except Exception as exc:
        return JsonResponse({
            "status": "unhealthy",
            "database": "error",
            "detail": str(exc),
        }, status=503)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("health/", health_check, name="health_check"),
]

# 开发环境：提供 MEDIA_URL 静态访问（生产建议由 Nginx/对象存储提供）
if getattr(settings, "DEBUG", False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
