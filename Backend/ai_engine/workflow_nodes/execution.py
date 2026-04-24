"""
画布节点执行入口：失败时更新 ``WorkflowExecution`` 并打日志。

与主 LangGraph ``workflow.py`` 大图为独立路径；供「按画布节点跑一步」类 API 调用。
"""

from __future__ import annotations

import logging
from typing import Any, Mapping

from ai_engine.models import WorkflowExecution
from ai_engine.workflow_nodes import cost_context as cost_ctx
from ai_engine.workflow_nodes.registry import resolve_node_executor

logger = logging.getLogger(__name__)


def execute_canvas_node(
    *,
    node_type: str,
    config: Mapping[str, Any],
    inputs: Mapping[str, Any],
    user_id: int | None,
    execution: WorkflowExecution | None = None,
    client_node_id: str = "",
) -> dict[str, Any]:
    """
    解析并执行单个画布节点。

    Args:
        node_type: 与 ``WorkflowGraphNode.node_type`` 一致。
        config: 节点配置（已脱敏）。
        inputs: 上游输入。
        user_id: 当前用户；解析 ``ut_*`` 时用于校验所有权。
        execution: 若提供且执行抛错，则将该执行标记为 failed 并写入 ``error_message``。
        client_node_id: 便于日志与计费维度。

    Returns:
        执行器返回的 dict。

    Raises:
        原样重新抛出执行器异常（在可选地更新 execution 之后）。
    """
    ex_id = execution.pk if execution is not None else None
    try:
        cost_ctx.set_llm_cost_context(execution_id=ex_id, client_node_id=client_node_id or "")
        executor = resolve_node_executor(node_type, user_id=user_id)
        cfg: dict[str, Any] = dict(config)
        if user_id is not None:
            cfg["_runtime_user_id"] = user_id
        return dict(executor.execute(config=cfg, inputs=inputs))
    except Exception as exc:
        logger.exception(
            "canvas node failed type=%s client_node_id=%s user_id=%s",
            node_type,
            client_node_id,
            user_id,
        )
        if execution is not None:
            WorkflowExecution.objects.filter(pk=execution.pk).update(
                status="failed",
                error_message=str(exc)[:4000],
                output_data={
                    "failed_node_type": node_type,
                    "client_node_id": client_node_id,
                    "error": str(exc),
                },
            )
        raise
    finally:
        cost_ctx.clear_llm_cost_context()
