from __future__ import annotations

import os
from dataclasses import dataclass
from typing import IO, Optional

from django.conf import settings


@dataclass(frozen=True)
class OssConfig:
    endpoint: str
    access_key_id: str
    access_key_secret: str
    bucket: str
    prefix: str


def _get_oss_config() -> Optional[OssConfig]:
    endpoint = (os.getenv("OSS_ENDPOINT") or "").strip()
    access_key_id = (os.getenv("OSS_ACCESS_KEY_ID") or "").strip()
    access_key_secret = (os.getenv("OSS_ACCESS_KEY_SECRET") or "").strip()
    bucket = (os.getenv("OSS_BUCKET") or "").strip()
    # 默认与当前 OSS 目录结构保持一致：Bucket 根下有一层 media/ 目录
    # 如需关闭/自定义，可在环境变量 OSS_PREFIX 中覆盖（留空则无前缀）
    prefix = os.getenv("OSS_PREFIX")
    if prefix is None:
        prefix = "media"
    prefix = str(prefix).strip()
    if not (endpoint and access_key_id and access_key_secret and bucket):
        return None
    return OssConfig(
        endpoint=endpoint,
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        bucket=bucket,
        prefix=prefix,
    )


def oss_enabled() -> bool:
    return _get_oss_config() is not None


def _oss_bucket():
    cfg = _get_oss_config()
    if cfg is None:
        raise RuntimeError("OSS is not configured. Set OSS_ENDPOINT/OSS_ACCESS_KEY_ID/OSS_ACCESS_KEY_SECRET/OSS_BUCKET.")
    try:
        import oss2  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("OSS is configured but python package 'oss2' is not installed.") from e
    auth = oss2.Auth(cfg.access_key_id, cfg.access_key_secret)
    return oss2.Bucket(auth, cfg.endpoint, cfg.bucket)


def _apply_prefix(key: str) -> str:
    """
    Map application rel_path -> OSS object key, supporting optional OSS_PREFIX.
    Examples:
      OSS_PREFIX="media/" + "uploads/u1/a.png" -> "media/uploads/u1/a.png"
      OSS_PREFIX="media"  + "uploads/..."      -> "media/uploads/..."
    """
    cfg = _get_oss_config()
    if cfg is None:
        return key
    k = (key or "").lstrip("/").replace("\\", "/")
    p = (cfg.prefix or "").strip().replace("\\", "/").strip("/")
    if not p:
        return k
    return f"{p}/{k}" if k else f"{p}/"


def put_bytes(*, key: str, data: bytes, content_type: str = "") -> None:
    b = _oss_bucket()
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    b.put_object(_apply_prefix(key), data, headers=headers or None)


def put_fileobj(*, key: str, fp: IO[bytes], content_type: str = "") -> None:
    b = _oss_bucket()
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    b.put_object(_apply_prefix(key), fp, headers=headers or None)


def get_stream(*, key: str):
    """
    Return an OSS GetObjectResult-like object with `.read()` and `.resp`.
    """
    b = _oss_bucket()
    return b.get_object(_apply_prefix(key))


def object_exists(*, key: str) -> bool:
    b = _oss_bucket()
    try:
        return bool(b.object_exists(_apply_prefix(key)))
    except Exception:
        return False


def media_root() -> str:
    return str(getattr(settings, "MEDIA_ROOT", "media"))

