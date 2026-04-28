"""
Django 项目配置入口。

按主题拆分为同包内子模块，便于维护；环境变量仍统一由 ``Backend/.env`` 提供。
导入顺序有依赖（如 CORS 依赖 DEBUG、Celery 依赖 TIME_ZONE），请勿随意调整。
"""

from __future__ import annotations

from .paths import BASE_DIR

from .security import *
from .features import *
from .applications import *
from .database import *
from .cache_conf import *
from .auth_passwords import *
from .i18n_time_static import *
from .cors import *
from .rest_jwt import *
from .channels_conf import *
from .celery_conf import *
from .ninja_conf import *
from .ai_providers import *
from .langsmith_conf import *
from .screen_agent import *
from .social_auth import *
from .logging_conf import LOGGING
