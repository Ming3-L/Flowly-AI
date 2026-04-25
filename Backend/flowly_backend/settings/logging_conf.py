"""日志。"""

import os


def _truthy(name: str) -> bool:
    return str(os.getenv(name, "") or "").strip().lower() in ("1", "true", "yes", "on")


_AUTO_REPLY_SILENT = _truthy("FLOWLY_AUTO_REPLY_SILENT")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        # runserver 的访问日志（"HTTP GET /..."）来自 django.server；默认降噪
        "django.server": {
            # 默认直接丢弃（避免任何访问日志刷屏）
            "handlers": ["null"],
            "level": "CRITICAL",
            "propagate": False,
        },
        # 第三方 HTTP 客户端日志（例如 httpx/urllib3）默认不刷屏
        "httpx": {
            "handlers": ["null"],
            "level": "CRITICAL",
            "propagate": False,
        },
        "urllib3": {
            "handlers": ["null"],
            "level": "CRITICAL",
            "propagate": False,
        },
        "ai_engine": {
            "handlers": ["console"],
            # 默认 INFO，避免 OCR/轮询等高频日志刷屏；需要排查时可用环境变量打开 DEBUG
            "level": os.getenv("AI_ENGINE_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        # 自动回复相关：可通过 FLOWLY_AUTO_REPLY_SILENT=1 一键静默
        "ai_engine.auto_reply": {
            "handlers": ["null"] if _AUTO_REPLY_SILENT else ["console"],
            "level": "CRITICAL" if _AUTO_REPLY_SILENT else os.getenv("AI_ENGINE_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "ai_engine.desktop_screen_agent": {
            "handlers": ["null"] if _AUTO_REPLY_SILENT else ["console"],
            "level": "CRITICAL" if _AUTO_REPLY_SILENT else os.getenv("AI_ENGINE_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "ai_engine.auto_reply_api": {
            "handlers": ["null"] if _AUTO_REPLY_SILENT else ["console"],
            "level": "CRITICAL" if _AUTO_REPLY_SILENT else os.getenv("AI_ENGINE_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}
