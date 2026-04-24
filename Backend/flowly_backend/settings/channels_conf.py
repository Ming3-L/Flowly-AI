"""Django Channels / Redis。"""

import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

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
