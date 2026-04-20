"""
ASGI config for flowly_backend project.

Supports HTTP (Django + Ninja), WebSocket, and SSE streaming via Django Channels.
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flowly_backend.settings")

# Initialise Django ASGI app early so the AppRegistry is ready before
# any code that imports ORM models runs.
django_asgi_app = get_asgi_application()

# WebSocket URL patterns
websocket_urlpatterns = URLRouter([
    # WebSocket route for workflow event streaming
    # ws://host/ws/workflow/<thread_id>/
    # Consumer: ai_engine.consumers.WorkflowStreamConsumer
])

# Import consumers after Django setup (triggers AppRegistry)
from ai_engine.routing import websocket_urlpatterns as workflow_ws_patterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(workflow_ws_patterns))
        ),
    }
)
