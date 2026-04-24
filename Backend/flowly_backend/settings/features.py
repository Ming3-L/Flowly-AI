"""Flowly 业务特性开关（环境变量）。"""

import os

FLOWLY_ADMIN_REGISTER_INVITE = os.getenv("FLOWLY_ADMIN_REGISTER_INVITE", "").strip()
FLOWLY_SUPERUSER_REGISTER_INVITE = os.getenv("FLOWLY_SUPERUSER_REGISTER_INVITE", "").strip()
FLOWLY_AUTO_REPLY_MODEL_KEY = os.getenv("FLOWLY_AUTO_REPLY_MODEL_KEY", "gpt-4o").strip()
FLOWLY_AUTO_REPLY_USE_SUBPROCESS = os.getenv("FLOWLY_AUTO_REPLY_USE_SUBPROCESS", "0").lower() in (
    "1",
    "true",
    "yes",
)
