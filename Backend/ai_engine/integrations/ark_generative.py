"""
火山方舟「生图 / 生视频」能力（与 Chat Completions 独立）。

基于官方 ``volcenginesdkarkruntime.Ark``：
- 文生图：``client.images.generate(...)``
- 文生视频：``client.content_generation.tasks.create`` + ``tasks.get`` 轮询

安装：``pip install 'volcengine-python-sdk[ark]'``
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from ai_engine.integrations import get_ai_provider_settings

logger = logging.getLogger(__name__)

def _require_ark_sdk():
    try:
        from volcenginesdkarkruntime import Ark  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "未安装火山方舟 SDK。请在 Backend 环境执行：pip install 'volcengine-python-sdk[ark]'"
        ) from exc
    return Ark


def build_ark_client() -> Any:
    Ark = _require_ark_sdk()
    s = get_ai_provider_settings()
    key = (s.language.doubao_ark_api_key or "").strip()
    if not key:
        raise ValueError("请配置 ARK_API_KEY 或 DOUBAO_API_KEY（与方舟控制台一致）。")
    base = (s.language.doubao_ark_base_url or "https://ark.cn-beijing.volces.com/api/v3").strip().rstrip("/")
    return Ark(base_url=base, api_key=key)


def ark_images_generate_url(
    *,
    model_id: str,
    prompt: str,
    size: str = "2K",
    watermark: bool = False,
) -> str:
    """文生图，返回首张图片 URL。"""
    client = build_ark_client()
    mid = (model_id or "").strip()
    if not mid:
        raise ValueError("图像生成需要 model_id（方舟模型 id，如 doubao-seedream-5-0-260128）。")
    p = (prompt or "").strip()
    if not p:
        raise ValueError("图像生成需要非空 prompt。")
    resp = client.images.generate(
        model=mid,
        prompt=p,
        size=size,
        response_format="url",
        watermark=watermark,
    )
    data = getattr(resp, "data", None)
    if data is None and isinstance(resp, dict):
        data = resp.get("data")
    if not data:
        raise RuntimeError(f"图像生成无 data 字段：{resp!r}")
    first = data[0]
    url = getattr(first, "url", None)
    if url is None and isinstance(first, dict):
        url = first.get("url")
    if not (url or "").strip():
        raise RuntimeError(f"图像生成未返回 url：{resp!r}")
    return str(url).strip()


def _result_to_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    md = getattr(obj, "model_dump", None)
    if callable(md):
        try:
            d = md()
            if isinstance(d, dict):
                return d
        except Exception:
            pass
    try:
        return json.loads(json.dumps(obj, default=lambda o: getattr(o, "__dict__", str(o))))
    except Exception:
        return {"repr": repr(obj)}


def _find_http_url(obj: Any, *, prefer_video: bool) -> str:
    """在 SDK 返回结构里尽量找出媒体 URL。

    注意：视频生成结果里常同时包含 cover 图片与 video 文件；prefer_video=True 时优先抓视频相关字段。
    """
    seen: set[int] = set()

    def walk(x: Any, parent_key: str = "") -> str:
        i = id(x)
        if i in seen:
            return ""
        seen.add(i)
        if isinstance(x, str):
            s = x.strip()
            if s.startswith("http://") or s.startswith("https://"):
                if prefer_video:
                    pk = (parent_key or "").lower()
                    # 若字段名已明确指向 video，则接受该 URL（即使无 .mp4 后缀）
                    if "video" in pk or pk in ("download_url", "file_url"):
                        return s
                    if any(s.lower().endswith(ext) for ext in (".mp4", ".webm", ".mov")):
                        return s
                    if "video" in s.lower() or "/video" in s.lower():
                        return s
                    # prefer_video 模式下：不要把封面图等链接当成最终视频结果
                    return ""
                else:
                    if any(s.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif")):
                        return s
                    if "image" in s.lower() or "tos-" in s.lower():
                        return s
                return ""
            return ""
        if isinstance(x, dict):
            for k in ("url", "video_url", "cover_url", "download_url", "file_url", "uri"):
                if k in x:
                    u = walk(x[k], parent_key=str(k))
                    if u:
                        return u
            for v in x.values():
                u = walk(v, parent_key=parent_key)
                if u:
                    return u
        if isinstance(x, (list, tuple)):
            for it in x:
                u = walk(it, parent_key=parent_key)
                if u:
                    return u
        return ""

    return walk(obj)


def ark_video_generate_poll(
    *,
    model_id: str,
    prompt_text: str,
    image_url: str | None = None,
    duration: int | None = None,
    resolution: str | None = None,
    ratio: str | None = None,
    watermark: bool | None = None,
    camera_fixed: bool | None = None,
    draft: bool | None = None,
    poll_interval_s: float = 3.0,
    timeout_s: float = 600.0,
) -> tuple[str, dict[str, Any]]:
    """
    文生视频 /（可选）参考图生视频（异步任务），返回 (视频 URL 或空字符串, 原始结果 dict)。
    """
    client = build_ark_client()
    mid = (model_id or "").strip()
    if not mid:
        raise ValueError("视频生成需要 model_id（如 doubao-seedance-2-0-260128）。")
    text = (prompt_text or "").strip()
    if not text:
        raise ValueError("视频生成需要非空文案。")

    content: list[dict[str, Any]] = [{"type": "text", "text": text}]
    ref = (image_url or "").strip()
    if ref:
        # 方舟多模态 content 结构与 chat/completions 类似：
        # [{"type":"text","text":"..."},{"type":"image_url","image_url":{"url":"..."}}]
        content.append({"type": "image_url", "image_url": {"url": ref}})

    create_kwargs: dict[str, Any] = {"model": mid, "content": content}
    if duration is not None:
        create_kwargs["duration"] = int(duration)
    if resolution:
        create_kwargs["resolution"] = str(resolution)
    if ratio:
        create_kwargs["ratio"] = str(ratio)
    if watermark is not None:
        create_kwargs["watermark"] = bool(watermark)
    if camera_fixed is not None:
        create_kwargs["camera_fixed"] = bool(camera_fixed)
    if draft is not None:
        create_kwargs["draft"] = bool(draft)

    create_result = client.content_generation.tasks.create(**create_kwargs)
    task_id = getattr(create_result, "id", None)
    if task_id is None and isinstance(create_result, dict):
        task_id = create_result.get("id")
    if not task_id:
        raise RuntimeError(f"创建视频任务失败：{create_result!r}")
    logger.info("ark video task created model=%s task_id=%s", mid, task_id)

    deadline = time.monotonic() + float(timeout_s)
    last_dump: dict[str, Any] = {}
    while time.monotonic() < deadline:
        get_result = client.content_generation.tasks.get(task_id=task_id)
        last_dump = _result_to_dict(get_result)
        status = str(last_dump.get("status") or getattr(get_result, "status", "") or "")
        logger.info("ark video task poll task_id=%s status=%s", task_id, status)
        if status == "succeeded":
            url = _find_http_url(last_dump, prefer_video=True) or _find_http_url(get_result, prefer_video=True)
            if not url:
                logger.warning("ark video task succeeded but no video url parsed task_id=%s keys=%s", task_id, list(last_dump.keys())[:40])
            return url, last_dump
        if status == "failed":
            err = last_dump.get("error") or getattr(get_result, "error", "")
            logger.error("ark video task failed task_id=%s error=%s", task_id, err)
            raise RuntimeError(f"视频生成失败：{err}")
        time.sleep(float(poll_interval_s))

    raise TimeoutError(f"视频生成超时（{timeout_s}s），最后状态：{last_dump!r}")
