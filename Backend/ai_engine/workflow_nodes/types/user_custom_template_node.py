from __future__ import annotations

from typing import Any, Mapping

from langchain_core.messages import HumanMessage  # pyright: ignore[reportMissingImports]

from ai_engine.cost_tracker import record_llm_cost_from_canvas_context
from ai_engine.models import UserCustomNodeType
from ai_engine.workflow import get_chat_model
from ai_engine.workflow_nodes import cost_context as cost_ctx
from ai_engine.workflow_nodes.base import NodeExecutor


class UserCustomTemplateNodeExecutor(NodeExecutor):
    """按用户模板绑定 provider + model_name，密钥走 ``get_chat_model`` 统一来源。"""

    __slots__ = ("template",)

    def __init__(self, template: UserCustomNodeType) -> None:
        self.template = template

    def execute(self, *, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        route = self.template.provider_route
        model = self.template.model_name
        merged = {**self.template.default_config, **dict(config)}
        temperature = float(merged.get("temperature", 0.7))
        max_tokens = int(merged.get("max_tokens", 1024))
        llm = get_chat_model(
            route,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = str(inputs.get("text") or inputs.get("query") or "").strip()
        if not text:
            return {"text": "", "error": "empty_input", "hint": "请在 inputs.text 或 inputs.query 中提供内容。"}
        out = llm.invoke([HumanMessage(content=text)])
        content = getattr(out, "content", str(out))
        cctx = cost_ctx.get_llm_cost_context()
        if cctx and cctx.execution_id:
            record_llm_cost_from_canvas_context(
                cctx.execution_id,
                out,
                logical_node_name="canvas_user_template",
                model_fallback=model,
                client_node_id=cctx.client_node_id,
            )
        return {"text": content, "provider": route, "model": model}
