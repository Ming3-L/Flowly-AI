from __future__ import annotations

import logging
import urllib.error
import urllib.request
from io import BytesIO
from typing import Any, Mapping
from urllib.parse import urlparse

from langchain_core.messages import HumanMessage, SystemMessage  # pyright: ignore[reportMissingImports]

from ai_engine.cost_tracker import record_llm_cost_from_canvas_context
from ai_engine.integrations import get_ai_provider_settings
from ai_engine.workflow_nodes import cost_context as cost_ctx
from ai_engine.workflow_nodes.base import NodeExecutor
from ai_engine.workflow_nodes.canvas_llm import get_chat_model_for_canvas_node

logger = logging.getLogger(__name__)

_MAX_AUDIO_BYTES = 25 * 1024 * 1024


def _download_url_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Flowly-AI/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 — 画布节点由用户配置 URL
        chunk = resp.read(_MAX_AUDIO_BYTES + 1)
    if len(chunk) > _MAX_AUDIO_BYTES:
        raise ValueError(f"音频文件过大（>{_MAX_AUDIO_BYTES // (1024 * 1024)}MB），请缩短或使用较小文件。")
    return chunk


def _transcribe_remote_audio_openai(url: str) -> str:
    """
    使用 OpenAI Whisper 兼容接口将 ``audio_url`` 转为文本。

    需要 ``OPENAI_API_KEY``；与豆包密钥独立（Whisper 目前走 OpenAI 官方或兼容网关）。
    """
    s = get_ai_provider_settings()
    if not (s.language.openai_api_key or "").strip():
        raise ValueError(
            "已提供 audio_url 但未提供转写文本：请配置 OPENAI_API_KEY 以启用 Whisper 自动转写，"
            "或在 inputs.text / inputs.transcript 中传入已有转写。"
        )
    raw = _download_url_bytes(url)
    path = urlparse(url).path.lower()
    ext = path.rsplit(".", 1)[-1] if "." in path else "mp3"
    if ext not in ("mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "ogg"):
        ext = "mp3"
    buf = BytesIO(raw)
    buf.name = f"audio.{ext}"

    try:
        from openai import OpenAI  # pyright: ignore[reportMissingImports]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("缺少 openai 包，无法调用 Whisper API。") from exc

    client = OpenAI(
        api_key=s.language.openai_api_key,
        base_url=(s.language.openai_base_url or "https://api.openai.com/v1").rstrip("/"),
    )
    model = (s.audio.openai_whisper_model or "whisper-1").strip()
    tr = client.audio.transcriptions.create(model=model, file=buf)
    text = (getattr(tr, "text", None) or "").strip()
    if not text:
        raise RuntimeError("Whisper 返回空转写，请检查音频是否可识别。")
    return text


class AudioNodeExecutor(NodeExecutor):
    """
    音频节点

    - 若 ``inputs.transcript`` / ``text`` 已有内容：按 ``systemPrompt`` 调用大模型做摘要等。
    - 若仅有 ``audio_url``：在配置了 ``OPENAI_API_KEY`` 时先用 Whisper 转写，再走大模型（同上）。
    """

    def execute(self, *, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        transcript = str(
            inputs.get("transcript") or inputs.get("text") or inputs.get("query") or ""
        ).strip()
        audio_url = str(
            inputs.get("audio_url") or inputs.get("url") or config.get("audio_url") or ""
        ).strip()
        if not audio_url:
            media = inputs.get("media")
            if isinstance(media, list):
                for it in media:
                    if isinstance(it, dict) and str(it.get("type") or "").strip().lower() == "audio" and it.get("url"):
                        audio_url = str(it.get("url") or "").strip()
                        if audio_url:
                            break

        asr_used = False
        if not transcript and audio_url:
            try:
                transcript = _transcribe_remote_audio_openai(audio_url)
                asr_used = True
            except (urllib.error.URLError, ValueError, RuntimeError) as exc:
                logger.warning("audio ASR failed url=%s err=%s", audio_url[:80], exc)
                return {
                    "text": "",
                    "error": "missing_transcript",
                    "hint": str(exc),
                    "audio_url": audio_url or None,
                }

        if not transcript:
            return {
                "text": "",
                "error": "missing_transcript",
                "hint": "请提供 inputs.text / inputs.transcript，或可公网访问的 audio_url（需 OPENAI_API_KEY 做 Whisper）。",
                "audio_url": audio_url or None,
            }

        system = str(
            config.get("systemPrompt")
            or config.get("system_prompt")
            or "你是助手。根据用户提供的音频转写文本，输出简洁的中文要点列表。"
        ).strip()
        llm, route, model_id = get_chat_model_for_canvas_node(config, max_tokens_default=1024, streaming=False)

        messages: list[Any] = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=transcript))

        out = llm.invoke(messages)
        content = getattr(out, "content", str(out))
        cctx = cost_ctx.get_llm_cost_context()
        if cctx and cctx.execution_id:
            record_llm_cost_from_canvas_context(
                cctx.execution_id,
                out,
                logical_node_name="canvas_audio",
                model_fallback=model_id,
                client_node_id=cctx.client_node_id,
            )
        return {
            "text": content,
            "audio_url": audio_url or None,
            "provider": route,
            "model": model_id,
            "asr_used": asr_used,
        }
