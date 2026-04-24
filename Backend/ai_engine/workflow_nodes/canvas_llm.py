"""
画布节点共用的语言模型解析与实例化。

优先使用 ``config.modelKey``（项目预设，见 ``ai_model_catalog``）；
仍兼容旧版 ``config.provider`` / ``config.model``（含 ``ep-`` 方舟接入点）。
"""

from __future__ import annotations

from typing import Any, Mapping

from langchain_core.language_models.chat_models import BaseChatModel  # pyright: ignore[reportMissingImports]

from ai_engine.ai_model_catalog import get_user_preset_llm_overrides, resolve_route_and_model_id
from ai_engine.workflow import get_chat_model


def resolve_canvas_llm_route_and_model(config: Mapping[str, Any]) -> tuple[str, str]:
    """根据节点配置解析路由名与模型 id（用于 ``get_chat_model`` 与计费回退名）。"""
    route, model_id, _ = resolve_route_and_model_id(config)
    return route, model_id


def get_chat_model_for_canvas_node(
    config: Mapping[str, Any],
    *,
    max_tokens_default: int = 1024,
    streaming: bool = False,
) -> tuple[BaseChatModel, str, str]:
    """
    Returns:
        ``(llm, route, model_id)``
    """
    route, model_id, cat_key = resolve_route_and_model_id(config)
    temperature = float(config.get("temperature", 0.7))
    max_tokens = int(config.get("max_tokens", max_tokens_default))
    uid: int | None = None
    ru = config.get("_runtime_user_id")
    if ru is not None and str(ru).strip().isdigit():
        uid = int(str(ru).strip())
    overrides = get_user_preset_llm_overrides(cat_key, uid)
    llm = get_chat_model(
        route,
        model=model_id,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
        **overrides,
    )
    return llm, route, model_id
