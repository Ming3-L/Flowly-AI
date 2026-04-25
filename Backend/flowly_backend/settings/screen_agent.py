"""本机屏幕代理（YOLO 区域检测等）可选环境变量。"""

import os
from pathlib import Path

from .paths import BASE_DIR

# 默认权重放在后端模块内（随项目一起迁移/部署）
_DEFAULT_YOLO = BASE_DIR / "ai_engine" / "desktop_screen_agent" / "weights" / "best.pt"

_env_weights = (os.getenv("FLOWLY_SCREEN_YOLO_WEIGHTS") or "").strip()
if _env_weights:
    FLOWLY_SCREEN_YOLO_WEIGHTS = _env_weights
elif _DEFAULT_YOLO.is_file():
    FLOWLY_SCREEN_YOLO_WEIGHTS = str(_DEFAULT_YOLO.resolve())
else:
    FLOWLY_SCREEN_YOLO_WEIGHTS = ""

FLOWLY_SCREEN_YOLO_TOLERANCE_PX = int(os.getenv("FLOWLY_SCREEN_YOLO_TOLERANCE_PX", "20"))
