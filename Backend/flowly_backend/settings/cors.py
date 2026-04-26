"""CORS。"""

import os

from .security import DEBUG

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("true", "1", "yes", "y", "on")


def _env_csv(name: str, default_csv: str) -> list[str]:
    raw = os.getenv(name, default_csv) or ""
    return [v.strip() for v in raw.split(",") if v.strip()]


# 兼容历史拼写：之前误写为 CORS_ALLOWED_ORIGINS（少了 ED），Railway 上可能已经配置了正确变量名
# - 正确：CORS_ALLOWED_ORIGINS
# - 旧误写：CORS_ALLOWED_ORIGINS
_cors_allowed_origins_env = (
    os.getenv("CORS_ALLOWED_ORIGINS") or os.getenv("CORS_ALLOWED_ORIGINS") or ""
).strip()

CORS_ALLOWED_ORIGINS = (
    [v.strip() for v in _cors_allowed_origins_env.split(",") if v.strip()]
    if _cors_allowed_origins_env
    else _env_csv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,https://ming3-l.github.io",
    )
)

CORS_ALLOW_ALL_ORIGINS = _env_bool("CORS_ALLOW_ALL_ORIGINS", DEBUG)
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
