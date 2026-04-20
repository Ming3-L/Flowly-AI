"""
WebSocket URL routing for ai_engine.

Connect via: ws://host/ws/workflow/<thread_id>/
"""

from django.urls import re_path

from .consumers import WorkflowStreamConsumer

websocket_urlpatterns = [
    re_path(
        r"^ws/workflow/(?P<thread_id>[0-9a-f-]+)/$",
        WorkflowStreamConsumer.as_asgi(),
    ),
]
