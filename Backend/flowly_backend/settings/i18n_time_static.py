"""语言、时区、静态与媒体。"""

import os

from .paths import BASE_DIR

LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "zh-hans")
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Shanghai")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
