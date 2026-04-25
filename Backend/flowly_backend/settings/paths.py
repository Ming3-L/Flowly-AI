"""路径与 .env 加载（须最先导入）。"""

from pathlib import Path

from dotenv import load_dotenv

# Backend/ 根目录：本文件位于 flowly_backend/settings/paths.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 支持 UTF-8 BOM；并尝试仓库根目录 .env（部分用户把 .env 放在 Flowly-AI/ 而非 Backend/）
for _p in (BASE_DIR / ".env", BASE_DIR.parent / ".env"):
    if _p.is_file():
        load_dotenv(_p, encoding="utf-8-sig")
