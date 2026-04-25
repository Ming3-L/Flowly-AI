"""Flowly 业务特性开关（环境变量）。"""

import os

FLOWLY_ADMIN_REGISTER_INVITE = os.getenv("FLOWLY_ADMIN_REGISTER_INVITE", "").strip()
FLOWLY_SUPERUSER_REGISTER_INVITE = os.getenv("FLOWLY_SUPERUSER_REGISTER_INVITE", "").strip()
# 方舟等第三方拉取本地上传图时，需填「外网可访问」站点根（无尾斜杠），用于把 /api/media/public?... 拼成绝对 URL
FLOWLY_PUBLIC_BASE_URL = os.getenv("FLOWLY_PUBLIC_BASE_URL", "").strip().rstrip("/")
FLOWLY_AUTO_REPLY_MODEL_KEY = os.getenv("FLOWLY_AUTO_REPLY_MODEL_KEY", "gpt-4o").strip()
FLOWLY_AUTO_REPLY_USE_SUBPROCESS = os.getenv("FLOWLY_AUTO_REPLY_USE_SUBPROCESS", "0").lower() in (
    "1",
    "true",
    "yes",
)
