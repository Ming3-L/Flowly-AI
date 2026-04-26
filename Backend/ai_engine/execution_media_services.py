"""
执行结果相关的媒体处理：远程拉取、格式转换、OpenAI 文生图 / TTS（可选）。
"""

from __future__ import annotations

import base64
import logging
import json
import os
import uuid
import asyncio
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


def _guess_audio_format(*, url: str = "", content_type: str | None = None) -> str:
    """
    OpenSpeech ASR v3 支持 pcm/wav/mp3/ogg（具体以账号开通为准）。
    这里做一个尽量保守的推断：默认 wav，其次按 content-type / 扩展名。
    """
    ct = (content_type or "").lower()
    u = (url or "").lower()
    if "audio/mpeg" in ct or u.endswith(".mp3"):
        return "mp3"
    if "audio/ogg" in ct or "audio/opus" in ct or u.endswith(".ogg") or u.endswith(".opus"):
        return "ogg"
    if "audio/wav" in ct or "audio/x-wav" in ct or u.endswith(".wav"):
        return "wav"
    if "audio/pcm" in ct or u.endswith(".pcm"):
        return "pcm"
    return "wav"


def _require_volcengine_audio():
    try:
        from volcengine_audio import (  # type: ignore[import-not-found]
            VolcengineAsrRequestV3,
            VolcengineAsrFunctionsV3,
            STTAudioFormatV3,
        )
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("缺少 volcengine-audio 包，请安装：pip install volcengine-audio") from exc
    return VolcengineAsrRequestV3, VolcengineAsrFunctionsV3, STTAudioFormatV3


async def _openspeech_asr_v3_ws_transcribe_async(
    *,
    audio: bytes,
    audio_format: str,
    uid: str,
    language: str,
    rate: int,
    appid: str,
    access_token: str,
    ws_url: str,
    resource_id: str,
    model_name: str,
    timeout_s: float = 120.0,
) -> dict:
    """
    OpenSpeech ASR v3（bigmodel_nostream）最小实现：发送 full_request + 音频数据，
    读取服务端 full responses，尝试解析出最终文本。

    说明：
    - OpenSpeech ASR v3 为 WebSocket 二进制帧协议，不是普通 HTTP。
    - 这里使用 volcengine-audio SDK 生成/解析帧，避免手写协议。
    """
    try:
        import websockets  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("缺少 websockets 包，请安装：pip install websockets") from exc

    VolcengineAsrRequestV3, VolcengineAsrFunctionsV3, STTAudioFormatV3 = _require_volcengine_audio()

    fmt_map = {
        "wav": STTAudioFormatV3.wav,
        "pcm": STTAudioFormatV3.pcm,
        "mp3": STTAudioFormatV3.mp3,
        "ogg": STTAudioFormatV3.ogg,
    }
    stt_fmt = fmt_map.get((audio_format or "").lower())
    if stt_fmt is None:
        raise ValueError(f"不支持的音频格式: {audio_format}（支持 wav/pcm/mp3/ogg）")

    req = VolcengineAsrRequestV3(
        user={"uid": (uid or "flowly")},
        audio={
            "format": stt_fmt,
            "rate": int(rate or 16000),
            "bits": 16,
            "channel": 1,
            "language": (language or "zh-CN"),
        },
        request={
            "model_name": (model_name or "bigmodel"),
            "enable_itn": True,
            "enable_punc": True,
        },
    )
    full = VolcengineAsrFunctionsV3.generate_asr_full_client_request(
        sequence=1,
        request_params=req.model_dump(exclude_none=True),
        compression=True,
    )

    headers = {
        "X-Api-App-Key": (appid or "").strip(),
        "X-Api-Access-Key": (access_token or "").strip(),
        "X-Api-Resource-Id": (resource_id or "").strip(),
        "X-Api-Connect-Id": str(uuid.uuid4()),
        "User-Agent": "Flowly-AI/1.0",
    }
    if not headers["X-Api-App-Key"] or not headers["X-Api-Access-Key"]:
        raise ValueError("未配置 OPENSPEECH_APPID / OPENSPEECH_ACCESS_TOKEN，无法调用 OpenSpeech ASR。")

    # 发送策略：按较小 chunk 切分，避免单帧过大；最后一帧单独发送。
    chunk_size = 20 * 1024
    seq = 2

    last_response: dict = {}
    best_text = ""
    pieces: list[str] = []

    async with websockets.connect(ws_url, extra_headers=headers, open_timeout=15) as ws:
        await ws.send(full)

        for i in range(0, len(audio), chunk_size):
            chunk = audio[i : i + chunk_size]
            # volcengine-audio SDK 负责生成 audio-only 帧
            audio_req = VolcengineAsrFunctionsV3.generate_asr_audio_only_request(
                sequence=seq,
                audio=chunk,
                compress=True,
            )
            seq += 1
            await ws.send(audio_req)

        # 读取返回：直到超时，或解析到“足够像最终文本”的字段为止
        deadline = asyncio.get_running_loop().time() + float(timeout_s)
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                break
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=min(5.0, remaining))
            except asyncio.TimeoutError:
                break

            try:
                parsed = VolcengineAsrFunctionsV3.parse_response(msg)
            except Exception:
                continue

            if isinstance(parsed, dict):
                last_response = parsed

                # 常见字段兜底：不同版本可能字段名略有差异
                cand = ""
                for k in ("text", "result", "message", "transcript"):
                    v = parsed.get(k)
                    if isinstance(v, str) and v.strip():
                        cand = v.strip()
                        break
                payload = parsed.get("payload")
                if not cand and isinstance(payload, dict):
                    for k in ("text", "result", "transcript", "utterance"):
                        v = payload.get(k)
                        if isinstance(v, str) and v.strip():
                            cand = v.strip()
                            break
                if cand:
                    pieces.append(cand)
                    best_text = cand

                # 若服务端明确返回结束标志，提前退出
                ended = parsed.get("is_end") or parsed.get("end") or parsed.get("finished")
                if isinstance(ended, bool) and ended:
                    break

    out_text = (best_text or "").strip()
    if not out_text and pieces:
        out_text = pieces[-1].strip()
    return {
        "text": out_text,
        "raw": last_response,
    }


def openspeech_asr_transcribe_url(
    *,
    audio_url: str,
    uid: str = "flowly",
    language: str | None = None,
    rate: int | None = None,
    timeout_s: float = 120.0,
) -> tuple[str, dict]:
    """
    OpenSpeech ASR（v3 WS，bigmodel_nostream）把远程音频 URL 转写为文本。

    返回：(text, raw_dict)
    """
    from ai_engine.integrations.secrets_loader import get_openspeech_settings

    url = (audio_url or "").strip()
    if not url:
        raise ValueError("audio_url 为空")

    raw, ct = fetch_url_bytes(url, max_bytes=25 * 1024 * 1024)
    fmt = _guess_audio_format(url=url, content_type=ct)

    cfg = get_openspeech_settings()
    lang = (language or cfg.asr_language or "zh-CN").strip()
    r = int(rate or cfg.asr_audio_rate or 16000)
    ws_url = (cfg.asr_ws_url or "").strip()
    rid = (cfg.asr_resource_id or "").strip()
    mname = (cfg.asr_model_name or "bigmodel").strip()

    # 同步入口：节点/HTTP handler 均为同步函数，内部用 asyncio.run
    try:
        d = asyncio.run(
            _openspeech_asr_v3_ws_transcribe_async(
                audio=raw,
                audio_format=fmt,
                uid=uid,
                language=lang,
                rate=r,
                appid=cfg.appid,
                access_token=cfg.access_token,
                ws_url=ws_url,
                resource_id=rid,
                model_name=mname,
                timeout_s=timeout_s,
            )
        )
    except RuntimeError:
        # 若上层已有事件循环（极少数场景），退回到新 loop
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            d = loop.run_until_complete(
                _openspeech_asr_v3_ws_transcribe_async(
                    audio=raw,
                    audio_format=fmt,
                    uid=uid,
                    language=lang,
                    rate=r,
                    appid=cfg.appid,
                    access_token=cfg.access_token,
                    ws_url=ws_url,
                    resource_id=rid,
                    model_name=mname,
                    timeout_s=timeout_s,
                )
            )
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    text = str((d or {}).get("text") or "").strip()
    if not text:
        raise RuntimeError(
            "OpenSpeech ASR 未解析到文本。若你的账号需要不同的 resource_id/ws_url，"
            "请配置 OPENSPEECH_ASR_RESOURCE_ID / OPENSPEECH_ASR_WS_URL 后重试。"
        )
    return text, dict((d or {}).get("raw") or {})


def openspeech_auc_submit_and_poll_url(
    *,
    audio_url: str,
    uid: str = "flowly",
    language: str | None = None,
    timeout_s: float = 300.0,
    poll_interval_s: float = 2.0,
) -> tuple[str, dict]:
    """
    OpenSpeech 录音文件识别（AUC，大模型标准版）：HTTP submit + query 轮询。

    文档要点（2026）：
    - submit: POST https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit
    - query : POST https://openspeech.bytedance.com/api/v3/auc/bigmodel/query
    - ASR2.0 resource id 常见为：volc.seedasr.auc
    - Header 使用：X-Api-App-Key / X-Api-Access-Key / X-Api-Resource-Id / X-Api-Request-Id / X-Api-Sequence
    """
    from ai_engine.integrations.secrets_loader import get_openspeech_settings

    url = (audio_url or "").strip()
    if not url:
        raise ValueError("audio_url 为空")

    cfg = get_openspeech_settings()
    appid = (cfg.appid or "").strip()
    token = (cfg.access_token or "").strip()
    if not appid or not token:
        raise ValueError("未配置 OPENSPEECH_APPID / OPENSPEECH_ACCESS_TOKEN")

    submit_url = (cfg.auc_submit_url or "").strip()
    query_url = (cfg.auc_query_url or "").strip()
    rid = (cfg.auc_resource_id or "volc.seedasr.auc").strip()
    if not submit_url or not query_url:
        raise ValueError("未配置 OPENSPEECH_AUC_SUBMIT_URL / OPENSPEECH_AUC_QUERY_URL")

    req_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "X-Api-App-Key": appid,
        "X-Api-Access-Key": token,
        "X-Api-Resource-Id": rid,
        "X-Api-Request-Id": req_id,
        "X-Api-Sequence": "-1",
        "User-Agent": "Flowly-AI/1.0",
    }

    payload = {
        "user": {"uid": (uid or "flowly")},
        "audio": {"url": url},
        "request": {
            "model_name": "bigmodel",
            "enable_itn": True,
            "enable_punc": True,
        },
    }
    lang = (language or "").strip()
    if lang:
        payload["audio"]["language"] = lang

    submit_req = urllib.request.Request(
        submit_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(submit_req, timeout=120) as resp:  # noqa: S310
            raw = resp.read(_MAX_DOWNLOAD + 1)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(_MAX_DOWNLOAD + 1)  # type: ignore[attr-defined]
        except Exception:
            body = b""
        raise RuntimeError(f"OpenSpeech AUC submit HTTP 错误: {exc} body={body[:300]!r}") from exc

    obj = json.loads(raw.decode("utf-8", errors="replace"))
    task_id = (
        str(obj.get("id") or "")
        or str((obj.get("resp") or {}).get("id") or "")
        or str((obj.get("result") or {}).get("id") or "")
    ).strip()
    if not task_id:
        raise RuntimeError(f"OpenSpeech AUC submit 未返回 task id: {obj!r}")

    import time as _t

    deadline = _t.monotonic() + float(timeout_s)
    last: dict = obj
    while True:
        now = _t.monotonic()
        if now >= deadline:
            raise TimeoutError(f"OpenSpeech AUC 识别超时（{timeout_s}s）。最后响应：{last!r}")

        qpayload = {"id": task_id}
        qreq = urllib.request.Request(
            query_url,
            data=json.dumps(qpayload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(qreq, timeout=120) as resp:  # noqa: S310
                qraw = resp.read(_MAX_DOWNLOAD + 1)
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read(_MAX_DOWNLOAD + 1)  # type: ignore[attr-defined]
            except Exception:
                body = b""
            raise RuntimeError(f"OpenSpeech AUC query HTTP 错误: {exc} body={body[:300]!r}") from exc

        last = json.loads(qraw.decode("utf-8", errors="replace"))
        # 兼容多种返回形态：直接 text / result.text / utterances
        text = ""
        for k in ("text", "transcript", "result"):
            v = last.get(k)
            if isinstance(v, str) and v.strip():
                text = v.strip()
                break
        if not text and isinstance(last.get("result"), dict):
            r = last["result"]
            for k in ("text", "transcript"):
                v = r.get(k)
                if isinstance(v, str) and v.strip():
                    text = v.strip()
                    break
        if text:
            return text, last

        # 未完成时通常只回状态码；继续轮询
        _t.sleep(float(poll_interval_s))


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
