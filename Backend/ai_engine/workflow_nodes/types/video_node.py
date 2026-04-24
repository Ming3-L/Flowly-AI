from __future__ import annotations

import re
import logging
from typing import Any, Mapping

from langchain_core.messages import HumanMessage, SystemMessage  # pyright: ignore[reportMissingImports]

from ai_engine.cost_tracker import record_llm_cost_from_canvas_context
from ai_engine.integrations.ark_generative import ark_video_generate_poll
from ai_engine.models import AIModelCatalogEntry
from ai_engine.workflow_nodes import cost_context as cost_ctx
from ai_engine.workflow_nodes.base import NodeExecutor
from ai_engine.workflow_nodes.canvas_llm import get_chat_model_for_canvas_node
from ai_engine.workflow_nodes.catalog_resolve import catalog_entry_for_model_key

logger = logging.getLogger(__name__)

class VideoNodeExecutor(NodeExecutor):
    """
    视频相关节点（文案侧）：根据 ``inputs`` 中的说明调用大模型做摘要/脚本等。

    ``inputs`` 约定
    ----------------
    - ``text`` / ``query`` / ``description``：需要模型处理的正文
    - ``video_url``：仅作元数据回传（不做自动抽帧；后续可接视频理解 API）。
    """

    def execute(self, *, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        # 兜底：若下游只拿到了 inputs.media（由画布串联自动透传），尝试从中取 video_url
        media = inputs.get("media")
        if not inputs.get("video_url") and isinstance(media, list):
            for it in media:
                if isinstance(it, dict) and str(it.get("type") or "").strip().lower() == "video" and it.get("url"):
                    inputs = dict(inputs)
                    inputs["video_url"] = str(it.get("url") or "").strip()
                    break

        body = str(
            inputs.get("description")
            or inputs.get("text")
            or inputs.get("query")
            or ""
        ).strip()
        if not body:
            return {
                "text": "",
                "error": "empty_input",
                "hint": "请在 inputs.description / inputs.text 中提供需要模型处理的视频相关文案或说明。",
                "video_url": str(inputs.get("video_url") or inputs.get("url") or "") or None,
            }

        system = str(
            config.get("systemPrompt")
            or config.get("system_prompt")
            or "你是助手。根据用户提供的视频相关文字说明，输出结构化摘要（可含时间线/镜头建议等，视输入而定）。"
        ).strip()

        entry = catalog_entry_for_model_key(config)
        if entry is not None and str(entry.api_kind or "") == AIModelCatalogEntry.ApiKind.ARK_VIDEO_GEN:
            mid = (entry.model_id or "").strip()
            logger.info("canvas video: use ark_video_gen modelKey=%s model_id=%s", getattr(entry, "catalog_key", ""), mid)
            if not mid:
                return {
                    "text": "",
                    "error": "missing_model_id",
                    "hint": f"目录项「{entry.label}」未配置 model_id，请在后台模型目录中填写方舟视频模型 id。",
                    "video_url": str(inputs.get("video_url") or inputs.get("url") or "") or None,
                }
            # 画布上游常把图片节点输出写成「签名 URL + 文生图说明」；
            # 文生视频 prompt 不应包含这些 URL。
            prompt_text = re.sub(r"https?://\\S+", "", body).strip()
            # 避免把「--dur 5」「--wm true」之类 CLI 风格参数塞进 prompt，部分 Seedance 版本会报 InvalidParameter
            prompt_text = re.sub(r"--\\w+\\s+[^\\s]+", "", prompt_text).strip()
            prompt_text = re.sub(r"--\\w+\\b", "", prompt_text).strip()
            if not prompt_text:
                prompt_text = body
            try:
                vid_url, raw = ark_video_generate_poll(
                    model_id=mid,
                    prompt_text=prompt_text,
                    duration=int(config.get("video_duration") or 5),
                    resolution=str(config.get("video_resolution") or "720p"),
                    ratio=str(config.get("video_ratio") or "16:9"),
                    watermark=bool(config.get("video_watermark") or False),
                    poll_interval_s=float(config.get("video_poll_interval_s") or 3.0),
                    timeout_s=float(config.get("video_timeout_s") or 600.0),
                )
            except Exception as exc:
                logger.exception("canvas video: ark_video_gen failed model_id=%s", mid)
                return {
                    "text": "",
                    "error": "ark_video_gen_failed",
                    "hint": str(exc),
                    "video_url": None,
                }
            lines = [f"（文生视频：{entry.label}）"]
            if vid_url:
                lines.insert(0, vid_url)
            else:
                # 直接把原始返回（截断）打到 text，方便前端直接看到字段结构
                import json

                raw_txt = json.dumps(raw, ensure_ascii=False)[:2000]
                lines.insert(
                    0,
                    "任务已完成，但未解析到视频 URL。下面是 video_generation（前 2000 字符），请把这段发我以便适配字段：\n"
                    + raw_txt,
                )
            return {
                "text": "\n".join(lines),
                "video_url": vid_url or None,
                "video_generation": raw,
                "provider": "doubao",
                "model": mid,
            }

        llm, route, model_id = get_chat_model_for_canvas_node(config, max_tokens_default=2048, streaming=False)

        messages: list[Any] = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=body))

        out = llm.invoke(messages)
        content = getattr(out, "content", str(out))
        cctx = cost_ctx.get_llm_cost_context()
        if cctx and cctx.execution_id:
            record_llm_cost_from_canvas_context(
                cctx.execution_id,
                out,
                logical_node_name="canvas_video",
                model_fallback=model_id,
                client_node_id=cctx.client_node_id,
            )
        return {
            "text": content,
            "video_url": str(inputs.get("video_url") or inputs.get("url") or "") or None,
            "provider": route,
            "model": model_id,
        }
