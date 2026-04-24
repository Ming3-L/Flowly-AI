"""
执行结果相关的媒体处理：远程拉取、格式转换、OpenAI 文生图 / TTS（可选）。
"""

from __future__ import annotations

import base64
import logging
import urllib.error
import urllib.request
from io import BytesIO
logger = logging.getLogger(__name__)

_MAX_DOWNLOAD = 30 * 1024 * 1024


def fetch_url_bytes(url: str, *, max_bytes: int = _MAX_DOWNLOAD) -> tuple[bytes, str | None]:
    """GET 远程资源，返回 (bytes, content_type_hint)。"""
    req = urllib.request.Request(url, headers={"User-Agent": "Flowly-AI/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
        raw = resp.read(max_bytes + 1)
        ct = resp.headers.get("Content-Type")
    if len(raw) > max_bytes:
        raise ValueError("资源过大，已拒绝下载。")
    return raw, ct


def convert_image_bytes(data: bytes, target: str) -> tuple[bytes, str]:
    """
    将图片字节转为 ``png`` / ``jpeg`` / ``webp``。

    Returns:
        ``(bytes, mime_type)``
    """
    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("请安装 Pillow 以支持图片格式转换：pip install Pillow") from exc

    im = Image.open(BytesIO(data))
    if im.mode in ("RGBA", "P") and target == "jpeg":
        im = im.convert("RGB")
    buf = BytesIO()
    t = target.lower()
    if t == "png":
        im.save(buf, format="PNG")
        return buf.getvalue(), "image/png"
    if t in ("jpg", "jpeg"):
        im.save(buf, format="JPEG", quality=92)
        return buf.getvalue(), "image/jpeg"
    if t == "webp":
        im.save(buf, format="WEBP", quality=85)
        return buf.getvalue(), "image/webp"
    raise ValueError(f"不支持的图片格式: {target}")


def openai_text_to_image_bytes(*, prompt: str, size: str = "1024x1024") -> tuple[bytes, str]:
    """调用 OpenAI Images，返回 PNG 字节（``dall-e-3`` 返回 URL 时服务端拉取）。"""
    from ai_engine.integrations import get_ai_provider_settings

    s = get_ai_provider_settings()
    key = (s.language.openai_api_key or "").strip()
    if not key:
        raise ValueError("未配置 OPENAI_API_KEY，无法文生图。")

    try:
        from openai import OpenAI  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("缺少 openai 包") from exc

    client = OpenAI(
        api_key=key,
        base_url=(s.language.openai_base_url or "https://api.openai.com/v1").rstrip("/"),
    )
    model = (s.image.openai_image_model or "dall-e-3").strip()
    p = (prompt or "").strip()[:4000]
    if not p:
        raise ValueError("prompt 为空")

    resp = client.images.generate(
        model=model,
        prompt=p,
        size=size if size in ("1024x1024", "1792x1024", "1024x1792") else "1024x1024",
        response_format="b64_json",
        n=1,
    )
    data = getattr(resp, "data", None) or []
    if not data:
        raise RuntimeError("文生图未返回数据")
    b64 = getattr(data[0], "b64_json", None)
    if not b64:
        raise RuntimeError("文生图未返回 b64_json")
    raw = base64.b64decode(b64)
    return raw, "image/png"


def openai_tts_bytes(*, text: str, voice: str = "alloy", response_format: str = "mp3") -> tuple[bytes, str]:
    """OpenAI TTS，返回音频字节。"""
    from ai_engine.integrations import get_ai_provider_settings

    s = get_ai_provider_settings()
    key = (s.language.openai_api_key or "").strip()
    if not key:
        raise ValueError("未配置 OPENAI_API_KEY，无法语音合成。")

    try:
        from openai import OpenAI  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("缺少 openai 包") from exc

    client = OpenAI(
        api_key=key,
        base_url=(s.language.openai_base_url or "https://api.openai.com/v1").rstrip("/"),
    )
    t = (text or "").strip()[:4096]
    if not t:
        raise ValueError("文本为空，无法合成语音")

    fmt = response_format if response_format in ("mp3", "opus", "aac", "flac", "wav", "pcm") else "mp3"
    speech = client.audio.speech.create(
        model=(s.audio.openai_tts_model or "tts-1").strip(),
        voice=voice if voice in ("alloy", "echo", "fable", "onyx", "nova", "shimmer") else "alloy",
        input=t,
        response_format=fmt,
    )
    content = getattr(speech, "content", None)
    if isinstance(content, (bytes, bytearray)):
        pass
    elif hasattr(speech, "read"):
        content = speech.read()
    elif hasattr(speech, "iter_bytes"):
        bio = BytesIO()
        for chunk in speech.iter_bytes():
            bio.write(chunk)
        content = bio.getvalue()
    else:
        raise RuntimeError("TTS 未返回二进制内容")
    mime = {
        "mp3": "audio/mpeg",
        "opus": "audio/opus",
        "aac": "audio/aac",
        "flac": "audio/flac",
        "wav": "audio/wav",
        "pcm": "audio/L16",
    }.get(fmt, "application/octet-stream")
    return bytes(content), mime
