"""
平台级 AI 密钥与端点：加密写入数据库，运行时由 ``secrets_loader`` 优先读取。

单例表 ``PlatformAIProviderSecrets``（pk=1）。密钥使用 Fernet（密钥由 Django SECRET_KEY 派生），
请勿在日志或 API 响应中泄露明文。
"""

from __future__ import annotations

import base64
import os
import hashlib
import json
import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken  # pyright: ignore[reportMissingModuleSource]
from django.conf import settings

logger = logging.getLogger(__name__)

SINGLETON_PK = 1


def _fernet() -> Fernet:
    raw = (getattr(settings, "SECRET_KEY", None) or "unsafe-dev-secret").encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def load_plain_entries() -> dict[str, str]:
    """解密得到 key->value；无记录或解密失败时返回空 dict。"""
    from ai_engine.models import PlatformAIProviderSecrets

    row = PlatformAIProviderSecrets.objects.filter(pk=SINGLETON_PK).first()
    if not row or not (row.encrypted_payload or "").strip():
        return {}
    try:
        raw = _fernet().decrypt(str(row.encrypted_payload).strip().encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
    except (InvalidToken, json.JSONDecodeError, OSError, ValueError) as e:
        logger.warning("PlatformAIProviderSecrets decrypt/parse failed: %s", e)
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in data.items():
        if not isinstance(k, str) or not k.strip():
            continue
        out[k.strip()] = "" if v is None else str(v)
    return out


def save_plain_entries(entries: dict[str, Any]) -> None:
    """整体替换写入（调用方已合并）。"""
    from ai_engine.models import PlatformAIProviderSecrets

    clean: dict[str, str] = {}
    for k, v in entries.items():
        if not isinstance(k, str) or not k.strip():
            continue
        clean[k.strip()] = "" if v is None else str(v)
    blob = _fernet().encrypt(json.dumps(clean, ensure_ascii=False).encode("utf-8")).decode("ascii")
    PlatformAIProviderSecrets.objects.update_or_create(
        pk=SINGLETON_PK,
        defaults={"encrypted_payload": blob},
    )
    from ai_engine.integrations.secrets_loader import clear_local_secrets_cache

    clear_local_secrets_cache()


def merge_entries_patch(patch: dict[str, Any]) -> None:
    """
    合并 PATCH：空字符串或 null 表示删除该 key 的数据库覆盖（回退到环境变量等）。
    """
    cur = load_plain_entries()
    for k, v in patch.items():
        if not isinstance(k, str) or not k.strip():
            continue
        key = k.strip()
        if v is None or (isinstance(v, str) and v.strip() == ""):
            cur.pop(key, None)
        else:
            cur[key] = str(v).strip()
    save_plain_entries(cur)


def seed_from_process_environ(*, replace: bool = False) -> int:
    """
    将当前进程内已设置的非空环境变量写入数据库（便于从 .env 迁库）。
    仅包含 ``managed_ai_config_key_names`` 中的 key。返回写入条数。
    """
    from ai_engine.integrations.secrets_loader import managed_ai_config_key_names

    names = set(managed_ai_config_key_names())
    if replace:
        cur: dict[str, str] = {}
    else:
        cur = load_plain_entries()
    n = 0
    for key in names:
        raw = os.environ.get(key)
        if raw is None or str(raw).strip() == "":
            continue
        cur[key] = str(raw).strip()
        n += 1
    if n > 0 or replace:
        save_plain_entries(cur)
    return n
