"""路径与 .env 加载（须最先导入）。"""

from pathlib import Path

from dotenv import load_dotenv

# Backend/ 根目录：本文件位于 flowly_backend/settings/paths.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")
