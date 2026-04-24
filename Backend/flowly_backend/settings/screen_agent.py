"""本机屏幕代理（YOLO 区域检测等）可选环境变量。"""

import os
from pathlib import Path

from .paths import BASE_DIR

# 仓库根目录下的 best.pt（与 Backend 平级）
_REPO_ROOT = BASE_DIR.parent
_DEFAULT_YOLO = _REPO_ROOT / "best.pt"

_env_weights = (os.getenv("FLOWLY_SCREEN_YOLO_WEIGHTS") or "").strip()
if _env_weights:
    FLOWLY_SCREEN_YOLO_WEIGHTS = _env_weights
elif _DEFAULT_YOLO.is_file():
    FLOWLY_SCREEN_YOLO_WEIGHTS = str(_DEFAULT_YOLO.resolve())
else:
    FLOWLY_SCREEN_YOLO_WEIGHTS = ""

FLOWLY_SCREEN_YOLO_TOLERANCE_PX = int(os.getenv("FLOWLY_SCREEN_YOLO_TOLERANCE_PX", "20"))
