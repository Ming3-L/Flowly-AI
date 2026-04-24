"""
工作流执行过程的可观测性：MySQL 持久化步骤 + Redis 热状态。

- DB：``WorkflowExecutionStep`` 记录每个节点的开始/结束、活动描述、模型路由。
- Redis：``flowly:wfexec:{id}:live`` 保存当前节点快照，便于监控与 WS 断线后快速查询
  （与 Channels 使用同一 REDIS_URL，但 key 前缀独立）。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# LangGraph 内置节点 → 中文说明（未传 activity 时的回退）
LANGGRAPH_NODE_ACTIVITY: dict[str, str] = {
    "router": "分析用户意图并决定执行路径",
    "approval_gate": "等待或处理人工审批",
    "parallel_executor": "并行启动多个子任务",
    "consolidate": "合并各并行分支的结果",
    "tool_executor": "调用工具并整理工具输出",
    "general_assistant": "使用大模型进行通用对话与推理",
    "finalize": "汇总并生成最终回复",
    "rag_retrieval": "检索知识库 / RAG 上下文",
}


def activity_for_langgraph_node(node: str, model_route: str | None = None) -> str:
    base = LANGGRAPH_NODE_ACTIVITY.get(node, f"执行节点「{node}」")
    if model_route:
        return f"{base}（模型：{model_route}）"
    return base


def activity_for_canvas_node(
    node_type: str,
    *,
    display_title: str = "",
    model_id: str = "",
    provider: str = "",
    text_process_mode: str = "",
) -> str:
    t = (node_type or "").strip().lower()
    label = (display_title or "").strip()
    head = f"「{label}」" if label else f"类型 {t or 'unknown'}"

    if t in ("chat", "ai_chat"):
        prov = (provider or "doubao").strip() or "doubao"
        mid = (model_id or "默认接入点").strip()
        return f"{head}：使用 {prov} 模型（{mid}）处理文本"
    if t == "text":
        pm = (text_process_mode or "llm").strip().lower()
        if pm == "template":
            return f"{head}：文本模板拼接（不调模型）"
        prov = (provider or "doubao").strip() or "doubao"
        mid = (model_id or "环境默认").strip()
        return f"{head}：大模型处理（{prov} / {mid}）"
    if t == "tool":
        return f"{head}：工具调用（占位/扩展）"
    if t == "condition":
        return f"{head}：条件判断"
    if t == "human_approval":
        return f"{head}：人工审批"
    if t == "parallel":
        return f"{head}：并行分支编排"
    if t.startswith("ut_"):
        return f"{head}：自定义模板节点"
    return f"{head}：执行画布节点"


def _redis_client():
    try:
        import redis

        url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        return redis.Redis.from_url(url, decode_responses=True)
    except Exception as exc:  # pragma: no cover
        logger.debug("redis client unavailable: %s", exc)
        return None


def redis_set_execution_live(execution_id: int | None, payload: dict[str, Any]) -> None:
    if not execution_id:
        return
    r = _redis_client()
    if r is None:
        return
    try:
        key = f"flowly:wfexec:{execution_id}:live"
        body = json.dumps(payload, ensure_ascii=False)
        r.setex(key, 7200, body)
    except Exception as exc:
        logger.warning("redis_set_execution_live failed: %s", exc)


def redis_clear_execution_live(execution_id: int | None) -> None:
    if not execution_id:
        return
    r = _redis_client()
    if r is None:
        return
    try:
        r.delete(f"flowly:wfexec:{execution_id}:live")
    except Exception as exc:
        logger.warning("redis_clear_execution_live failed: %s", exc)


def redis_get_execution_live(execution_id: int) -> dict[str, Any] | None:
    """读取当前执行快照（WS 断线或监控页轮询）。"""
    r = _redis_client()
    if r is None:
        return None
    try:
        raw = r.get(f"flowly:wfexec:{execution_id}:live")
        if not raw:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.debug("redis_get_execution_live failed: %s", exc)
        return None


def _persist_step_start_sync(
    execution_id: int,
    *,
    node_key: str,
    display_title: str = "",
    node_kind: str = "",
    activity: str = "",
    model_route: str = "",
) -> None:
    from ai_engine.models import WorkflowExecutionStep

    WorkflowExecutionStep.objects.create(
        execution_id=execution_id,
        node_key=node_key[:255],
        display_title=(display_title or node_key)[:512],
        node_kind=node_kind[:64],
        activity=activity[:4000],
        model_route=model_route[:64],
        status=WorkflowExecutionStep.Status.RUNNING,
        started_at=timezone.now(),
    )


def _persist_step_end_sync(
    execution_id: int,
    *,
    node_key: str,
    end_status: str,
) -> None:
    from ai_engine.models import WorkflowExecutionStep

    qs = WorkflowExecutionStep.objects.filter(
        execution_id=execution_id,
        node_key=node_key[:255],
        status=WorkflowExecutionStep.Status.RUNNING,
        finished_at__isnull=True,
    ).order_by("-id")
    row = qs.first()
    if row is None:
        return
    row.status = (
        WorkflowExecutionStep.Status.COMPLETED
        if end_status == "completed"
        else WorkflowExecutionStep.Status.FAILED
    )
    row.finished_at = timezone.now()
    row.save(update_fields=["status", "finished_at"])


persist_step_start = sync_to_async(_persist_step_start_sync)
persist_step_end = sync_to_async(_persist_step_end_sync)
