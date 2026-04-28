"""Django cache backend.

邮箱验证码等短期状态使用 Django cache（见 accounts.email_service）。

- 若配置了 REDIS_URL：使用 RedisCache，避免重启/多实例导致验证码丢失或不一致
- 否则：回退 LocMemCache（仅适合单进程/开发环境）
"""

from __future__ import annotations

import os

# 显式配置才启用 Redis 缓存，避免本地未启动 Redis 时“隐式走默认 localhost”导致功能不可用。
# 如需复用 Channels 的 Redis，可在环境中设置：CACHE_URL=$REDIS_URL
_cache_url = (os.getenv("CACHE_URL", "") or "").strip()

if _cache_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _cache_url,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "flowly-local",
        }
    }

