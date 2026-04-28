"""Celery。"""

import os
from urllib.parse import urlparse, urlunparse

from .channels_conf import REDIS_URL
from .i18n_time_static import TIME_ZONE

def _with_redis_db(url: str, db: int) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    u = urlparse(raw)
    return urlunparse(u._replace(path=f"/{int(db)}"))


# Defaults: use same Redis as Channels, but move Celery to DB 1.
_default_celery_redis = _with_redis_db(REDIS_URL, 1) or "redis://localhost:6379/1"
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", _default_celery_redis)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", _default_celery_redis)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600
CELERY_TASK_SOFT_TIME_LIMIT = 1800
CELERY_WORKER_CONCURRENCY = int(os.getenv("CELERY_WORKER_CONCURRENCY", "4"))
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_RESULT_EXPIRES = 86400
