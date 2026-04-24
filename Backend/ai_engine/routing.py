"""
WebSocket URL routing for ai_engine.

Connect via: ws://host/ws/workflow/<thread_id>/
"""

from django.urls import re_path

from .consumers import WorkflowStreamConsumer

websocket_urlpatterns = [
    # UUID 可能含大写十六进制；与 channel group ``workflow_{thread_id}`` 对齐前在 consumer 内统一小写
    re_path(
        r"^ws/workflow/(?P<thread_id>[0-9a-fA-F-]{36})/$",
        WorkflowStreamConsumer.as_asgi(),
    ),
]
