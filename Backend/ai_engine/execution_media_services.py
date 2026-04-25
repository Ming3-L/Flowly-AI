"""
执行结果相关的媒体处理：远程拉取、格式转换、OpenAI 文生图 / TTS（可选）。
"""

from __future__ import annotations

import base64
import logging
import json
import os
import uuid
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


def openspeech_tts_bytes(
    *,
    text: str,
    encoding: str = "mp3",
    voice_type: str | None = None,
    speed_ratio: float = 1.0,
    uid: str = "flowly",
) -> tuple[bytes, str]:
    """
    豆包语音（火山 OpenSpeech）HTTP 非流式 TTS v1。

    参考文档（2026-04）：https://www.volcengine.com/docs/6561/1257584
    - URL: https://openspeech.bytedance.com/api/v1/tts
    - Header: Authorization: Bearer;${token}   （分号分隔）
    - Response: JSON，其中 data 为 base64 音频
    """
    from ai_engine.integrations.secrets_loader import get_openspeech_settings

    cfg = get_openspeech_settings()
    appid = (cfg.appid or "").strip()
    token = (cfg.access_token or "").strip()
    if not appid or not token:
        raise ValueError("未配置 OPENSPEECH_APPID / OPENSPEECH_ACCESS_TOKEN，无法调用豆包语音合成。")

    url = (cfg.tts_url or "https://openspeech.bytedance.com/api/v1/tts").strip()
    cluster = (cfg.tts_cluster or "volcano_tts").strip()
    voice = (voice_type or cfg.tts_voice_type or "").strip()
    if not voice:
        # 给一个较常见的默认音色；生产建议显式配置
        voice = "zh_male_M392_conversation_wvae_bigtts"

    t = (text or "").strip()
    if not t:
        raise ValueError("文本为空，无法合成语音")
    t = t[:1024]  # 文档：1024 bytes（UTF-8）上限；这里做简单截断

    enc = (encoding or "mp3").strip().lower()
    if enc not in ("wav", "pcm", "ogg_opus", "mp3"):
        enc = "mp3"

    payload = {
        "app": {"appid": appid, "token": token, "cluster": cluster},
        "user": {"uid": (uid or "flowly")},
        "audio": {
            "voice_type": voice,
            "encoding": enc,
            "speed_ratio": float(speed_ratio or 1.0),
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": t,
            "operation": "query",
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer;{token}",
            "User-Agent": "Flowly-AI/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            raw = resp.read(_MAX_DOWNLOAD + 1)
    except urllib.error.HTTPError as exc:
        # 透出 OpenSpeech 的错误体，方便定位 401/配额/参数问题
        try:
            body = exc.read(_MAX_DOWNLOAD + 1)  # type: ignore[attr-defined]
        except Exception:
            body = b""
        detail = ""
        if body:
            try:
                obj = json.loads(body.decode("utf-8", errors="replace"))
                detail = f" code={obj.get('code')}, message={obj.get('message')}"
            except Exception:
                detail = f" body={body[:200]!r}"
        if int(getattr(exc, "code", 0) or 0) == 401:
            raise RuntimeError(
                "OpenSpeech TTS 鉴权失败（401 Unauthorized）。"
                "请检查 OPENSPEECH_APPID / OPENSPEECH_ACCESS_TOKEN 是否为同一应用，且 access_token 未过期。"
                + (f"{detail}" if detail else "")
            ) from exc
        raise RuntimeError(f"OpenSpeech TTS HTTP 错误: {exc}{detail}") from exc
    if len(raw) > _MAX_DOWNLOAD:
        raise ValueError("TTS 响应过大，已拒绝下载。")

    try:
        obj = json.loads(raw.decode("utf-8", errors="replace"))
    except Exception as exc:
        raise RuntimeError(f"OpenSpeech TTS 响应非 JSON: {raw[:200]!r}") from exc

    code = int(obj.get("code") or 0)
    msg = str(obj.get("message") or "")
    if code != 3000:
        raise RuntimeError(f"OpenSpeech TTS 失败: code={code}, message={msg}")

    b64 = str(obj.get("data") or "").strip()
    if not b64:
        raise RuntimeError("OpenSpeech TTS 未返回 data")

    audio = base64.b64decode(b64)
    mime = {
        "mp3": "audio/mpeg",
        "ogg_opus": "audio/ogg",
        "wav": "audio/wav",
        "pcm": "audio/L16",
    }.get(enc, "application/octet-stream")
    return audio, mime


def openspeech_v3_tts_bytes(
    *,
    text: str,
    encoding: str = "mp3",
    speaker: str | None = None,
    resource_id: str = "seed-tts-2.0",
    sample_rate: int = 24000,
    uid: str = "flowly",
) -> tuple[bytes, str]:
    """
    豆包语音（OpenSpeech）TTS v3 单向（HTTP）。

    - URL: https://openspeech.bytedance.com/api/v3/tts/unidirectional
    - Header（新版控制台推荐）:
        - X-Api-Key: {api_key/Access Token}
        - X-Api-Resource-Id: seed-tts-2.0 / seed-tts-1.0 ...
      Header（旧版控制台）:
        - X-Api-App-Id: {appid}
        - X-Api-Access-Key: {access_token}
        - X-Api-Resource-Id: seed-tts-2.0 / seed-tts-1.0 ...
    - Response: JSON，data 为 base64 音频
    """
    from ai_engine.integrations.secrets_loader import get_openspeech_settings

    cfg = get_openspeech_settings()
    appid = (cfg.appid or "").strip()
    token = (cfg.access_token or "").strip()
    api_key = (getattr(cfg, "api_key", "") or "").strip()
    if not (api_key or token):
        raise ValueError(
            "未配置 OpenSpeech 鉴权信息，无法调用豆包语音合成。请配置："
            "（新版控制台推荐）OPENSPEECH_API_KEY；或（旧版）OPENSPEECH_ACCESS_TOKEN + OPENSPEECH_APPID。"
        )

    url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
    rid = (resource_id or "").strip() or "seed-tts-2.0"
    if rid.startswith("seed-tts-2.0"):
        spk = (speaker or cfg.tts2_speaker or "").strip()
    else:
        spk = (speaker or cfg.tts_voice_type or "").strip()
    if not spk:
        spk = "zh_male_M392_conversation_wvae_bigtts"

    t = (text or "").strip()
    if not t:
        raise ValueError("文本为空，无法合成语音")
    t = t[:4000]

    enc = (encoding or "mp3").strip().lower()
    # v3 文档示例为 format=mp3；其余格式留给后续扩展
    if enc not in ("mp3", "wav", "pcm", "ogg_opus"):
        enc = "mp3"

    payload = {
        "user": {"uid": (uid or "flowly")},
        "req_params": {
            "text": t,
            "speaker": spk,
            "audio_params": {
                "format": enc,
                "sample_rate": int(sample_rate or 24000),
            },
        },
    }

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-Api-Resource-Id": rid,
        "X-Api-Request-Id": str(uuid.uuid4()),
        "User-Agent": "Flowly-AI/1.0",
    }
    # 新版控制台：使用 X-Api-Key
    if api_key:
        headers["X-Api-Key"] = api_key
    else:
        # 旧版控制台：使用 appid + access_token
        if not appid or not token:
            raise ValueError("未配置 OPENSPEECH_APPID / OPENSPEECH_ACCESS_TOKEN，无法调用豆包语音合成。")
        headers["X-Api-App-Id"] = appid
        headers["X-Api-Access-Key"] = token

    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            raw = resp.read(_MAX_DOWNLOAD + 1)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(_MAX_DOWNLOAD + 1)  # type: ignore[attr-defined]
        except Exception:
            body = b""
        detail = ""
        if body:
            try:
                obj = json.loads(body.decode("utf-8", errors="replace"))
                detail = f" code={obj.get('code')}, message={obj.get('message')}"
            except Exception:
                detail = f" body={body[:200]!r}"
        raise RuntimeError(f"OpenSpeech v3 TTS HTTP 错误: {exc}{detail}") from exc

    if len(raw) > _MAX_DOWNLOAD:
        raise ValueError("TTS 响应过大，已拒绝下载。")
    # v3（unidirectional）在部分实现下可能会返回多个 JSON 对象（例如 chunked 输出），
    # 这里用 streaming JSON 方式逐个解析并拼接音频片段。
    txt = raw.decode("utf-8", errors="replace").strip()
    dec = json.JSONDecoder()
    idx = 0
    objs: list[dict[str, Any]] = []
    try:
        while idx < len(txt):
            # 跳过空白
            while idx < len(txt) and txt[idx].isspace():
                idx += 1
            if idx >= len(txt):
                break
            obj, end = dec.raw_decode(txt, idx)
            if isinstance(obj, dict):
                objs.append(obj)
            idx = end
    except Exception as exc:
        raise RuntimeError(f"OpenSpeech v3 TTS 响应非 JSON: {raw[:200]!r}") from exc

    if not objs:
        raise RuntimeError(f"OpenSpeech v3 TTS 响应为空或无法解析: {raw[:200]!r}")

    chunks: list[bytes] = []
    for obj in objs:
        code = int(obj.get("code") or 0)
        msg = str(obj.get("message") or "")
        if code not in (0, 20000000):
            raise RuntimeError(f"OpenSpeech v3 TTS 失败: code={code}, message={msg}")
        b64 = str(obj.get("data") or "").strip()
        if b64:
            chunks.append(base64.b64decode(b64))

    if not chunks:
        raise RuntimeError("OpenSpeech v3 TTS 未返回 data")

    audio = b"".join(chunks)
    mime = {
        "mp3": "audio/mpeg",
        "ogg_opus": "audio/ogg",
        "wav": "audio/wav",
        "pcm": "audio/L16",
    }.get(enc, "application/octet-stream")
    return audio, mime
