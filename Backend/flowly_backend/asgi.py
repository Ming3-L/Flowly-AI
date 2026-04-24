"""
ASGI config for flowly_backend project.

Supports HTTP (Django + Ninja), WebSocket, and SSE streaming via Django Channels.
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.conf import settings
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flowly_backend.settings")

# Initialise Django ASGI app early so the AppRegistry is ready before
# any code that imports ORM models runs.
django_asgi_app = get_asgi_application()

# Import consumers after Django setup (triggers AppRegistry)
from ai_engine.routing import websocket_urlpatterns as workflow_ws_patterns

_ws_inner = AuthMiddlewareStack(URLRouter(workflow_ws_patterns))
# 开发环境放宽：直连 ws://localhost:8000 时 Origin 常为 http://localhost:5173，易触发校验失败。
# 生产环境仍启用 AllowedHostsOriginValidator。
if settings.DEBUG:
    _websocket_app = _ws_inner
else:
    _websocket_app = AllowedHostsOriginValidator(_ws_inner)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": _websocket_app,
    }
)
