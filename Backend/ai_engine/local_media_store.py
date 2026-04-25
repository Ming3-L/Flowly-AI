from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
import uuid
from typing import Any

from django.conf import settings

from ai_engine.models import LocalMediaAsset


def _sign_public_token(*, rel_path: str, exp: int, secret: str) -> str:
    msg = f"{rel_path}|{exp}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(msg + b"." + sig).decode("ascii").strip("=")


def build_public_url(rel_path: str, *, expires_days: int = 7) -> str:
    secret = str(getattr(settings, "SECRET_KEY", "") or "flowly")
    exp = int(time.time()) + 3600 * 24 * int(expires_days)
    token = _sign_public_token(rel_path=rel_path, exp=exp, secret=secret)
    return f"/api/media/public?token={token}"


def build_proxy_url(rel_path: str) -> str:
    return f"/api/media/proxy?path={rel_path}"


def absolutize_public_url(url: str) -> str:
    """
    将站内相对 URL（如 /api/media/public?...）补全为第三方可拉取的绝对地址。
    需在环境变量 FLOWLY_PUBLIC_BASE_URL 中配置站点根（无尾斜杠），例如 https://app.example.com
    """
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith("http://") or u.startswith("https://"):
        return u
    base = str(getattr(settings, "FLOWLY_PUBLIC_BASE_URL", "") or "").strip().rstrip("/")
    if base and u.startswith("/"):
        return f"{base}{u}"
    return u


def _ext_from_mime(mime: str, fallback: str) -> str:
    m = (mime or "").lower().strip()
    if m.startswith("image/"):
        if "png" in m:
            return ".png"
        if "webp" in m:
            return ".webp"
        if "jpeg" in m or "jpg" in m:
            return ".jpg"
        return ".png"
    if m.startswith("audio/"):
        if "mpeg" in m or "mp3" in m:
            return ".mp3"
        if "wav" in m:
            return ".wav"
        if "aac" in m:
            return ".aac"
        if "opus" in m:
            return ".opus"
        return ".mp3"
    if m.startswith("video/"):
        if "mp4" in m:
            return ".mp4"
        if "webm" in m:
            return ".webm"
        return ".mp4"
    return fallback


def save_local_media_bytes(
    *,
    user_id: int,
    kind: str,
    data: bytes,
    mime: str,
    original_name: str = "",
    source_url: str = "",
    folder: str = "generated",
) -> dict[str, Any]:
    """
    将 bytes 保存到 MEDIA_ROOT，并创建 LocalMediaAsset 记录。

    返回：{ rel_path, proxy_url, public_url, asset_id }
    """
    uid = int(user_id)
    k = str(kind or LocalMediaAsset.Kind.FILE)
    secret_folder = str(folder or "generated").strip().strip("/")
    ext = _ext_from_mime(mime, ".bin")
    fname = f"{uuid.uuid4().hex}{ext}"
    rel_path = f"{secret_folder}/u{uid}/{k}/{fname}"

    media_root = str(getattr(settings, "MEDIA_ROOT", "media"))
    abs_path = os.path.join(media_root, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(data)

    row = LocalMediaAsset.objects.create(
        user_id=uid,
        kind=k,
        original_name=(original_name or "").strip()[:255],
        mime=(mime or "").strip()[:128],
        size_bytes=int(len(data)),
        rel_path=rel_path,
        source_url=(source_url or "").strip()[:2048],
    )
    return {
        "asset_id": row.pk,
        "rel_path": rel_path,
        "proxy_url": build_proxy_url(rel_path),
        "public_url": build_public_url(rel_path),
    }

