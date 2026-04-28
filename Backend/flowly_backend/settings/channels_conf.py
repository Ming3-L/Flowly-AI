"""Django Channels / Redis。"""

import os
from urllib.parse import urlparse, urlunparse

def _ensure_redis_db(url: str, db: int) -> str:
    """
    Normalize redis URL to always include a DB index path like `/0`.
    Keeps query/fragment intact.
    """
    raw = (url or "").strip()
    if not raw:
        return ""
    u = urlparse(raw)
    path = (u.path or "").strip()
    if not path or path == "/":
        path = f"/{int(db)}"
    return urlunparse(u._replace(path=path))


# Prefer explicit REDIS_URL; fall back to CACHE_URL so users can set only one variable in hosting.
_redis_url = (os.getenv("REDIS_URL") or os.getenv("CACHE_URL") or "redis://localhost:6379/0").strip()
REDIS_URL = _ensure_redis_db(_redis_url, 0) or "redis://localhost:6379/0"

_inmem_flag = os.getenv("USE_INMEMORY_CHANNEL_LAYER", "").strip().lower()
_use_inmemory_channels = _inmem_flag in ("true", "1", "yes")

if _use_inmemory_channels:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
            },
        },
    }
