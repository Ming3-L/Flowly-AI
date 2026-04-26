"""数据库（DATABASE_URL 优先，否则 SQLite）。"""

from __future__ import annotations

import os
from urllib.parse import urlparse

from .paths import BASE_DIR

DATABASE_URL = (os.getenv("DATABASE_URL", "") or "").strip()
MYSQL_URL = (os.getenv("MYSQL_URL", "") or "").strip()
MYSQLHOST = (os.getenv("MYSQLHOST", "") or "").strip()
MYSQLPORT = (os.getenv("MYSQLPORT", "") or "").strip()
MYSQLUSER = (os.getenv("MYSQLUSER", "") or "").strip()
MYSQLPASSWORD = (os.getenv("MYSQLPASSWORD", "") or "").strip()
MYSQLDATABASE = (os.getenv("MYSQLDATABASE", "") or "").strip()


def _sqlite_default():
    return {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


def _parse_database_url(url: str):
    """
    支持常见平台的 DATABASE_URL：
    - mysql://user:pass@host:port/db
    - postgres://user:pass@host:port/db
    - postgresql://user:pass@host:port/db
    """
    p = urlparse(url)
    scheme = (p.scheme or "").lower()
    if scheme in ("postgres", "postgresql"):
        return {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": (p.path or "").lstrip("/"),
                "USER": p.username or "",
                "PASSWORD": p.password or "",
                "HOST": p.hostname or "",
                "PORT": str(p.port or 5432),
            }
        }
    if scheme == "mysql":
        return {
            "default": {
                "ENGINE": "django.db.backends.mysql",
                "NAME": (p.path or "").lstrip("/"),
                "USER": p.username or "",
                "PASSWORD": p.password or "",
                "HOST": p.hostname or "",
                "PORT": str(p.port or 3306),
                "OPTIONS": {
                    "charset": "utf8mb4",
                    "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
                },
            }
        }
    return None


def _mysql_from_railway_vars():
    """
    Railway MySQL 插件常见环境变量：
    MYSQLHOST / MYSQLPORT / MYSQLUSER / MYSQLPASSWORD / MYSQLDATABASE
    """
    if not (MYSQLHOST and MYSQLUSER and MYSQLPASSWORD and MYSQLDATABASE):
        return None
    port = MYSQLPORT or "3306"
    return {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": MYSQLDATABASE,
            "USER": MYSQLUSER,
            "PASSWORD": MYSQLPASSWORD,
            "HOST": MYSQLHOST,
            "PORT": port,
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }


_primary_db_url = DATABASE_URL or MYSQL_URL

if _primary_db_url:
    parsed = _parse_database_url(_primary_db_url)
    DATABASES = parsed or _sqlite_default()
else:
    DATABASES = _mysql_from_railway_vars() or _sqlite_default()
