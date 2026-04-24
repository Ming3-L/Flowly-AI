"""
异步 / 同步混用时，为 ``AIChatNodeExecutor`` 等提供当前执行的 ``execution_id`` 与画布 ``client_node_id``。

由 ``api._run_workflow_async``、``execute_canvas_node`` 在 try/finally 中维护，避免未传 execution 时写入 CostRecord。
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

_ctx: ContextVar[Optional["_CostCtx"]] = ContextVar("flowly_llm_cost_ctx", default=None)


@dataclass(slots=True)
class _CostCtx:
    execution_id: int | None
    client_node_id: str


def set_llm_cost_context(*, execution_id: int | None, client_node_id: str = "") -> None:
    """进入一次「可能调用 LLM」的范围前设置（须配对 ``clear_llm_cost_context``）。"""
    _ctx.set(_CostCtx(execution_id=execution_id, client_node_id=client_node_id or ""))


def clear_llm_cost_context() -> None:
    _ctx.set(None)


def get_llm_cost_context() -> _CostCtx | None:
    return _ctx.get()
