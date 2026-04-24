"""
用户自定义模型密钥：使用 Fernet 对称加密写入数据库（密钥派生自 Django SECRET_KEY）。

注意：若更换 ``SECRET_KEY``，已存密文将无法解密，用户需重新填写 API Key。
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken  # pyright: ignore[reportMissingImports]
from django.conf import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_user_secret(plain: str) -> str:
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_user_secret(token: str) -> str:
    if not (token or "").strip():
        return ""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return ""
