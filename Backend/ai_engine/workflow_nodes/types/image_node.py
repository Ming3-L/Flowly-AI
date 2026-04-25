from __future__ import annotations

from typing import Any, Mapping

from langchain_core.messages import HumanMessage  # pyright: ignore[reportMissingImports]

from ai_engine.cost_tracker import record_llm_cost_from_canvas_context
from ai_engine.integrations.ark_generative import ark_images_generate_url
from ai_engine.local_media_store import absolutize_public_url
from ai_engine.models import AIModelCatalogEntry
from ai_engine.workflow_nodes import cost_context as cost_ctx
from ai_engine.workflow_nodes.base import NodeExecutor
from ai_engine.workflow_nodes.canvas_llm import get_chat_model_for_canvas_node
from ai_engine.workflow_nodes.catalog_resolve import catalog_entry_for_model_key


class ImageNodeExecutor(NodeExecutor):
    """
    图像节点：多模态理解（图片 URL + 文本问题），模型由 ``config.provider`` / ``config.model`` 决定。

    ``inputs`` 约定
    ----------------
    - ``text`` / ``query``：对图片的提问（可选，缺省则用 ``config.captionPrompt``）
    - ``image_url`` / ``url``：可公网访问的图片地址

    若无 ``image_url``，则退化为纯文本调用（例如仅根据 ``text`` 生成说明）。
    """

    def execute(self, *, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        user_q = str(
            inputs.get("text")
            or inputs.get("query")
            or config.get("captionPrompt")
            or config.get("caption_prompt")
            or "请简要描述这张图片的主要内容。"
        ).strip()
        if not user_q:
            return {"text": "", "error": "empty_input", "hint": "请在 inputs.text / inputs.query 中提供问题或说明。"}

        image_url = (
            inputs.get("image_url")
            or inputs.get("url")
            or inputs.get("imageUrl")
            or config.get("image_url")
        )
        image_url = str(image_url).strip() if image_url else ""
        if not image_url:
            media = inputs.get("media")
            if isinstance(media, list):
                for it in media:
                    if isinstance(it, dict) and str(it.get("type") or "").strip().lower() == "image" and it.get("url"):
                        image_url = str(it.get("url") or "").strip()
                        if image_url:
                            break

        entry = catalog_entry_for_model_key(config)
        if entry is not None and str(entry.api_kind or "") == AIModelCatalogEntry.ApiKind.ARK_IMAGE_GEN:
            mid = (entry.model_id or "").strip()
            if not mid:
                return {
                    "text": "",
                    "error": "missing_model_id",
                    "hint": f"目录项「{entry.label}」未配置 model_id，请在后台模型目录中填写方舟生图模型 id。",
                    "image_url": image_url or None,
                }
            if image_url:
                return {
                    "text": "",
                    "error": "i2i_not_supported_yet",
                    "hint": "当前 Seedream 节点仅支持文生图（无参考图）。图生图请暂用方舟 SeedEdit 控制台或后续版本。",
                    "image_url": image_url,
                }
            size = str(config.get("image_size") or config.get("imageSize") or "2K").strip() or "2K"
            wm = bool(config.get("image_watermark") or config.get("imageWatermark") or False)
            try:
                gen_url = ark_images_generate_url(model_id=mid, prompt=user_q, size=size, watermark=wm)
            except Exception as exc:
                return {
                    "text": "",
                    "error": "ark_image_gen_failed",
                    "hint": str(exc),
                    "image_url": None,
                }
            return {
                # 下游节点（如视频节点）在画布串联时通常只会读取上游的 text；
                # 因此这里把 prompt 也写入 text，避免只传递 URL 导致下游 prompt 丢失。
                "text": f"{gen_url}\n\nPrompt: {user_q}\n\n（文生图：{entry.label}）",
                "image_url": gen_url,
                "generated_image_url": gen_url,
                "prompt": user_q,
                "mode": "ark_image_gen",
                "provider": "doubao",
                "model": mid,
            }

        llm, route, model_id = get_chat_model_for_canvas_node(config, max_tokens_default=1024, streaming=False)

        if image_url:
            abs_url = absolutize_public_url(image_url)
            msg = HumanMessage(
                content=[
                    {"type": "text", "text": user_q},
                    {"type": "image_url", "image_url": {"url": abs_url or image_url}},
                ]
            )
        else:
            msg = HumanMessage(content=user_q)

        out = llm.invoke([msg])
        content = getattr(out, "content", str(out))
        cctx = cost_ctx.get_llm_cost_context()
        if cctx and cctx.execution_id:
            record_llm_cost_from_canvas_context(
                cctx.execution_id,
                out,
                logical_node_name="canvas_image",
                model_fallback=model_id,
                client_node_id=cctx.client_node_id,
            )
        return {
            "text": content,
            "image_url": image_url or None,
            "mode": "multimodal" if image_url else "text_only",
            "provider": route,
            "model": model_id,
        }
