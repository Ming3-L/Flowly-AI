"""
媒体上传与受保护下载（用于工作流输入的图片/音频/视频等）。

设计目标：
- 允许前端将文件上传到后端（按用户隔离存储）
- 返回可在前端预览/在后端节点运行时引用的 URL（走鉴权 proxy）
"""

from __future__ import annotations

import mimetypes
import os
import time
import uuid
import hmac
import hashlib
import base64
from dataclasses import dataclass

from django.http import FileResponse, HttpRequest, HttpResponse
from django.utils.text import get_valid_filename
from ninja import Query, Router, Schema  # pyright: ignore[reportMissingImports]
from ninja.files import UploadedFile  # pyright: ignore[reportMissingImports]

from .auth import JWTAuth
from .models import LocalMediaAsset

media_router = Router(tags=["Media"], auth=JWTAuth())


class MediaUploadOut(Schema):
    name: str
    size: int
    mime: str
    path: str
    proxy_url: str
    public_url: str


def _safe_user_prefix(user_id: int) -> str:
    return f"uploads/u{int(user_id)}/"


def _guess_mime(name: str) -> str:
    mt, _ = mimetypes.guess_type(name)
    return mt or "application/octet-stream"


def _sign_public_token(*, rel_path: str, exp: int, secret: str) -> str:
    msg = f"{rel_path}|{exp}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest()
    tok = base64.urlsafe_b64encode(msg + b"." + sig).decode("ascii").strip("=")
    return tok


def _verify_public_token(token: str, *, secret: str) -> tuple[str, int] | None:
    if not token:
        return None
    pad = "=" * ((4 - (len(token) % 4)) % 4)
    try:
        raw = base64.urlsafe_b64decode((token + pad).encode("ascii"))
    except Exception:
        return None
    if b"." not in raw:
        return None
    msg, sig = raw.rsplit(b".", 1)
    exp_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, exp_sig):
        return None
    try:
        rel, exp_s = msg.decode("utf-8").split("|", 1)
        exp = int(exp_s)
    except Exception:
        return None
    return rel, exp


@media_router.post("/upload", response={200: MediaUploadOut})
def upload_media(request: HttpRequest, file: UploadedFile):
    """
    POST /api/media/upload (multipart/form-data)

    表单字段：file
    返回：受保护的 proxy_url（需 JWT），以及内部 path（用于传入工作流 inputs/context）
    """
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    if not u or not getattr(u, "id", None):
        return HttpResponse("Authentication required", status=401, content_type="text/plain; charset=utf-8")

    orig = get_valid_filename(getattr(file, "name", "") or "upload.bin")
    ext = os.path.splitext(orig)[1][:16]
    fname = f"{uuid.uuid4().hex}{ext}"
    rel_path = _safe_user_prefix(int(u.id)) + fname

    # 直接写入 MEDIA_ROOT 下（不依赖额外模型）
    from django.conf import settings

    media_root = str(getattr(settings, "MEDIA_ROOT", "media"))
    abs_path = os.path.join(media_root, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    with open(abs_path, "wb") as f:
        for chunk in file.chunks():
            f.write(chunk)

    mime = getattr(file, "content_type", None) or _guess_mime(orig)
    size = int(getattr(file, "size", 0) or 0)
    kind = (
        LocalMediaAsset.Kind.IMAGE
        if str(mime).startswith("image/")
        else LocalMediaAsset.Kind.AUDIO
        if str(mime).startswith("audio/")
        else LocalMediaAsset.Kind.VIDEO
        if str(mime).startswith("video/")
        else LocalMediaAsset.Kind.FILE
    )

    secret = str(getattr(settings, "SECRET_KEY", "") or "flowly")
    exp = int(time.time()) + 3600 * 24 * 7
    token = _sign_public_token(rel_path=rel_path, exp=exp, secret=secret)

    try:
        LocalMediaAsset.objects.create(
            user_id=int(u.id),
            kind=kind,
            original_name=orig,
            mime=mime,
            size_bytes=size,
            rel_path=rel_path,
            source_url="",
        )
    except Exception:
        # 不阻塞上传：即使落库失败，文件仍可用
        pass

    return 200, MediaUploadOut(
        name=orig,
        size=size,
        mime=mime,
        path=rel_path,
        proxy_url=f"/api/media/proxy?path={rel_path}",
        public_url=f"/api/media/public?token={token}",
    )


@media_router.get("/proxy")
def proxy_media(
    request: HttpRequest,
    path: str = Query(..., min_length=1, max_length=1024),
):
    """
    GET /api/media/proxy?path=...

    仅允许访问当前用户自己上传的文件（路径前缀 uploads/u{user_id}/）。
    """
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    if not u or not getattr(u, "id", None):
        return HttpResponse("Authentication required", status=401, content_type="text/plain; charset=utf-8")

    rel = (path or "").strip().lstrip("/").replace("\\", "/")
    if not rel.startswith(_safe_user_prefix(int(u.id))):
        return HttpResponse("Forbidden", status=403, content_type="text/plain; charset=utf-8")

    from django.conf import settings

    media_root = str(getattr(settings, "MEDIA_ROOT", "media"))
    abs_path = os.path.join(media_root, rel.replace("/", os.sep))
    if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        return HttpResponse("Not found", status=404, content_type="text/plain; charset=utf-8")

    # 尽量设置 content-type
    mime = _guess_mime(abs_path)
    return FileResponse(open(abs_path, "rb"), content_type=mime)


@media_router.get("/public", auth=None)
def public_media(
    request: HttpRequest,
    token: str = Query(..., min_length=16, max_length=4096),
):
    """
    GET /api/media/public?token=...

    用于让第三方模型服务拉取图片等资源（无 JWT），通过 HMAC token 限制路径与有效期。
    """
    from django.conf import settings

    secret = str(getattr(settings, "SECRET_KEY", "") or "flowly")
    parsed = _verify_public_token(token.strip(), secret=secret)
    if parsed is None:
        return HttpResponse("Forbidden", status=403, content_type="text/plain; charset=utf-8")
    rel, exp = parsed
    if int(time.time()) > int(exp):
        return HttpResponse("Expired", status=410, content_type="text/plain; charset=utf-8")

    rel = (rel or "").strip().lstrip("/").replace("\\", "/")
    if not rel.startswith("uploads/") and not rel.startswith("avatars/"):
        return HttpResponse("Forbidden", status=403, content_type="text/plain; charset=utf-8")

    media_root = str(getattr(settings, "MEDIA_ROOT", "media"))
    abs_path = os.path.join(media_root, rel.replace("/", os.sep))
    if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        return HttpResponse("Not found", status=404, content_type="text/plain; charset=utf-8")
    mime = _guess_mime(abs_path)
    return FileResponse(open(abs_path, "rb"), content_type=mime)

