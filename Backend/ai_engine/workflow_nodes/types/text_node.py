from __future__ import annotations

from typing import Any, Mapping

from langchain_core.messages import HumanMessage, SystemMessage  # pyright: ignore[reportMissingImports]

from ai_engine.cost_tracker import record_llm_cost_from_canvas_context
from ai_engine.workflow_nodes import cost_context as cost_ctx
from ai_engine.workflow_nodes.base import NodeExecutor
from ai_engine.workflow_nodes.canvas_llm import get_chat_model_for_canvas_node


class TextNodeExecutor(NodeExecutor):
    """
    文本节点

    - ``processMode`` = ``llm``（推荐）：用 ``config.provider`` / ``config.model`` 调用大模型，
      将 ``config.prompt`` 与上游 ``inputs.text`` 做占位符合并后作为用户消息（``systemPrompt`` 可选）。
    - ``processMode`` = ``template``：仅模板拼接，不调模型（须在节点上显式选择「仅模板」）。

    未配置 ``processMode`` 时默认 ``llm``，避免旧工作流/未保存字段时误走纯拼接、把「要求」当结果。
    """

    def execute(self, *, config: Mapping[str, Any], inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        process_mode = str(config.get("processMode") or config.get("process_mode") or "llm").strip().lower()
        prompt = str(config.get("prompt") or config.get("text") or "").strip()
        text = str(inputs.get("text") or inputs.get("query") or "").strip()

        if process_mode == "llm":
            if not prompt and not text:
                return {
                    "text": "",
                    "error": "empty_input",
                    "hint": "AI 模式下请填写「默认指令」或保证上游有 inputs.text。",
                    "mode": "llm",
                }
            had_placeholder = (
                "{{input}}" in prompt or "{{text}}" in prompt or "{{query}}" in prompt
            )
            merged = (
                prompt.replace("{{input}}", text)
                .replace("{{text}}", text)
                .replace("{{query}}", text)
                if prompt
                else text
            )
            # 未写占位符时，画布上游仍会写入 inputs.text；必须把上游正文一并交给模型
            if prompt and text.strip() and not had_placeholder:
                merged = f"{text.strip()}\n\n---\n\n{merged.strip()}"
            user_body = merged.strip()
            if not user_body:
                return {
                    "text": "",
                    "error": "empty_input",
                    "hint": "合并后的待处理文本为空。",
                    "mode": "llm",
                }
            system = str(config.get("systemPrompt") or config.get("system_prompt") or "").strip()
            llm, route, model_id = get_chat_model_for_canvas_node(config, max_tokens_default=1024, streaming=False)
            messages: list[Any] = []
            if system:
                messages.append(SystemMessage(content=system))
            messages.append(HumanMessage(content=user_body))
            out = llm.invoke(messages)
            content = getattr(out, "content", str(out))
            cctx = cost_ctx.get_llm_cost_context()
            if cctx and cctx.execution_id:
                record_llm_cost_from_canvas_context(
                    cctx.execution_id,
                    out,
                    logical_node_name="canvas_text_llm",
                    model_fallback=model_id,
                    client_node_id=cctx.client_node_id,
                )
            return {"text": content, "mode": "llm", "provider": route, "model": model_id}

        if not prompt:
            return {"text": text, "mode": "passthrough"}
        merged = (
            prompt.replace("{{input}}", text)
            .replace("{{text}}", text)
            .replace("{{query}}", text)
        )
        return {"text": merged.strip(), "mode": "template"}
