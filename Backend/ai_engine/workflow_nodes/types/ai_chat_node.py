from __future__ import annotations

from typing import Any, Mapping

from langchain_core.messages import HumanMessage, SystemMessage  # pyright: ignore[reportMissingImports]

from ai_engine.cost_tracker import record_llm_cost_from_canvas_context
from ai_engine.workflow_nodes import cost_context as cost_ctx
from ai_engine.workflow_nodes.base import NodeExecutor
from ai_engine.workflow_nodes.canvas_llm import get_chat_model_for_canvas_node


class AIChatNodeExecutor(NodeExecutor):
    """
    画布「对话」类节点：根据 ``config.model`` 等调用 ``get_chat_model``。

    密钥统一经 ``get_chat_model`` → ``get_ai_provider_settings()``，禁止从 config 读密钥。
    """

    def execute(self, *, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        llm, route, model_id = get_chat_model_for_canvas_node(config, max_tokens_default=1024, streaming=False)
        user_text = str(inputs.get("text") or inputs.get("query") or "").strip()
        if not user_text:
            return {"text": "", "error": "empty_input", "hint": "请在 inputs.text 或 inputs.query 中提供用户消息。"}
        system_prompt = str(config.get("systemPrompt") or config.get("system_prompt") or "").strip()
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=user_text))
        out = llm.invoke(messages)
        content = getattr(out, "content", str(out))
        cctx = cost_ctx.get_llm_cost_context()
        if cctx and cctx.execution_id:
            record_llm_cost_from_canvas_context(
                cctx.execution_id,
                out,
                logical_node_name="canvas_chat",
                model_fallback=model_id,
                client_node_id=cctx.client_node_id,
            )
        return {"text": content, "provider": route, "model": model_id, "requested_model": model_id}
