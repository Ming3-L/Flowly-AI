"""数据库（DATABASE_URL 优先，否则 SQLite）。"""

from __future__ import annotations

import os
from urllib.parse import urlparse

from .paths import BASE_DIR

def _env_first_nonempty(*names: str) -> str:
    for n in names:
        v = (os.getenv(n, "") or "").strip()
        if v:
            return v
    return ""


# ---- URL style (preferred) ----
# Railway 常见：
# - DATABASE_URL
# - MYSQL_URL（内部地址 mysql.railway.internal）
# - MYSQL_PUBLIC_URL（公网 proxy 地址）
DATABASE_URL = _env_first_nonempty("DATABASE_URL")
MYSQL_URL = _env_first_nonempty("MYSQL_URL", "MYSQL_PUBLIC_URL", "MYSQLPUBLICURL")

# ---- Discrete vars (fallback) ----
# Railway 插件环境变量有两套命名：无下划线（MYSQLHOST）和带下划线（MYSQL_HOST）
MYSQLHOST = _env_first_nonempty("MYSQLHOST", "MYSQL_HOST")
MYSQLPORT = _env_first_nonempty("MYSQLPORT", "MYSQL_PORT")
MYSQLUSER = _env_first_nonempty("MYSQLUSER", "MYSQL_USER")
MYSQLPASSWORD = _env_first_nonempty("MYSQLPASSWORD", "MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD")
MYSQLDATABASE = _env_first_nonempty("MYSQLDATABASE", "MYSQL_DATABASE")


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
    以及带下划线的同名变量（MYSQL_HOST 等）
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


# Railway 上经常同时注入：
# - DATABASE_URL（有时指向公网 proxy）
# - MYSQL_URL（通常是 mysql.railway.internal 内网地址，更稳定/更快）
# 因此这里优先使用 MYSQL_URL（含 MYSQL_PUBLIC_URL 兼容），再回退 DATABASE_URL。
_primary_db_url = MYSQL_URL or DATABASE_URL

if _primary_db_url:
    parsed = _parse_database_url(_primary_db_url)
    DATABASES = parsed or _sqlite_default()
else:
    DATABASES = _mysql_from_railway_vars() or _sqlite_default()
