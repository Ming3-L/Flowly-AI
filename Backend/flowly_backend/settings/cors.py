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


# CORS origins：
# - django-cors-headers 设置名：CORS_ALLOWED_ORIGINS
# - 我们允许通过环境变量配置；同时兼容历史误写变量名：CORS_ALLOW_ORIGINS（少了 ED）
#
# 注意：生产环境通常会设置环境变量；如果用“覆盖式”读取，容易把默认白名单（比如 GitHub Pages）
# 覆盖掉，导致浏览器出现“响应头(0)”的跨域屏蔽现象。
_DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://ming3-l.github.io",
]

_cors_allowed_origins_env = (
    os.getenv("CORS_ALLOWED_ORIGINS") or os.getenv("CORS_ALLOW_ORIGINS") or ""
).strip()

_env_origins = [v.strip() for v in _cors_allowed_origins_env.split(",") if v.strip()] if _cors_allowed_origins_env else []

# 合并：环境变量 + 默认白名单（去重、保持顺序）
_merged: list[str] = []
for v in [*_env_origins, *_DEFAULT_ALLOWED_ORIGINS]:
    if v and v not in _merged:
        _merged.append(v)

CORS_ALLOWED_ORIGINS = _merged

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
