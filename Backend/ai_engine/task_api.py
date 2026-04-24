"""
异步任务 API —— Phase 9：Celery

用于 Celery 任务管理的 Ninja 路由：
- 提交工作流异步执行
- 查询任务状态
- 取消运行中的任务
- 监控任务进度
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from django.http import HttpRequest
from ninja import Router, Schema  # pyright: ignore[reportMissingImports]
from pydantic import Field  # pyright: ignore[reportMissingImports]

from .auth import JWTAuth
from .models import Workflow, WorkflowExecution, Thread


# ─── 数据结构（Schema）─────────────────────────────────────────────────────────

class TaskStatusSchema(Schema):
    task_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None


class AsyncRunResponseSchema(Schema):
    task_id: str
    execution_id: int
    thread_id: str
    status: str
    message: str


class CancelResponseSchema(Schema):
    cancelled: bool
    task_id: str
    execution_id: int


class ProgressSchema(Schema):
    status: str
    progress: int
    current_node: str | None = None
    error: str | None = None


# ─── 路由（Router）───────────────────────────────────────────────────────────

router = Router(tags=["Async Tasks / Celery"], auth=JWTAuth())


@router.post("/run/async", response=AsyncRunResponseSchema)
def run_workflow_async(
    request: HttpRequest,
    workflow_id: int,
    query: str,
    context: dict[str, Any] | None = None,
    model_name: str = "openai",
    parallel_branches: list[str] | None = None,
    client_node_id: str = "",
) -> AsyncRunResponseSchema:
    """
    通过 Celery 提交工作流异步执行。

    会立即返回 task_id，前端可：
    - 轮询 GET /api/tasks/{task_id}/status 获取状态
    - 连接 WebSocket `/ws/workflow/{thread_id}/` 获取实时事件
    - 调用 POST /api/tasks/{task_id}/cancel 中止执行

    适用场景（优先使用本接口而不是 POST /api/workflows/run）：
    - 工作流执行时间可能超过 HTTP 超时
    - 需要中途取消的能力
    - 需要排队/调度执行
    """
    # 校验工作流
    try:
        workflow = Workflow.objects.get(id=workflow_id, is_active=True)
    except Workflow.DoesNotExist:
        return AsyncRunResponseSchema(
            task_id="",
            execution_id=0,
            thread_id="",
            status="error",
            message=f"工作流 {workflow_id} 不存在或未启用",
        )

    # 创建 thread 与 execution 记录
    thread_uuid = uuid.uuid4()
    u = getattr(request, "auth", None) or getattr(request, "user", None)
    thread = Thread.objects.create(
        thread_id=thread_uuid,
        user=u,
        workflow=workflow,
    )
    execution = WorkflowExecution.objects.create(
        workflow=workflow,
        thread=thread,
        status="pending",
        input_data={
            "query": query,
            "context": context or {},
            "client_node_id": client_node_id or "",
            "model_name": model_name,
            "parallel_branches": list(parallel_branches or []),
        },
    )

    # 投递到 Celery worker
    from ai_engine.tasks import run_workflow_task

    task = run_workflow_task.delay(
        execution_id=execution.id,
        workflow_id=workflow_id,
        thread_id=str(thread_uuid),
        user_query=query,
        context=context or {},
        model_name=model_name,
        parallel_branches=parallel_branches,
    )

    return AsyncRunResponseSchema(
        task_id=str(task.id),
        execution_id=execution.id,
        thread_id=str(thread_uuid),
        status="queued",
        message="工作流已加入队列",
    )


@router.get("/{task_id}/status", response=TaskStatusSchema)
def get_task_status(request: HttpRequest, task_id: str) -> TaskStatusSchema:
    """
    查询 Celery 任务状态。

    返回值：PENDING | STARTED | SUCCESS | FAILURE | REVOKED
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id)
    return TaskStatusSchema(
        task_id=task_id,
        status=result.status,
        result=result.result if result.ready() else None,
        error=str(result.info) if result.failed() else None,
    )


@router.post("/{task_id}/cancel", response=CancelResponseSchema)
def cancel_task(
    request: HttpRequest,
    task_id: str,
    execution_id: int,
) -> CancelResponseSchema:
    """
    取消一个运行中或排队中的 Celery 任务。

    Best-effort：若任务在本请求处理前已越过“可取消检查点”，仍可能继续完成。
    """
    from celery.result import AsyncResult

    # 在 Celery 中撤销任务
    AsyncResult(task_id).revoke(terminate=True)

    # 更新执行记录
    WorkflowExecution.objects.filter(id=execution_id).update(
        status="cancelled",
        error_message="Cancelled by user",
    )

    return CancelResponseSchema(
        cancelled=True,
        task_id=task_id,
        execution_id=execution_id,
    )


@router.get("/{execution_id}/progress", response=ProgressSchema)
def get_execution_progress(
    request: HttpRequest,
    execution_id: int,
) -> ProgressSchema:
    """
    Get real-time progress of a running execution from Django Cache.

    Updated by the workflow engine nodes via ai_engine.tasks.update_progress.
    """
    from django.core.cache import cache

    progress = cache.get(f"workflow_progress:{execution_id}")
    if progress:
        return ProgressSchema(
            status=progress.get("status", "running"),
            progress=progress.get("progress", 0),
            current_node=progress.get("current_node"),
            error=progress.get("error"),
        )

    # 回退：返回数据库状态
    try:
        exec_obj = WorkflowExecution.objects.get(id=execution_id)
        return ProgressSchema(
            status=exec_obj.status,
            progress=100 if exec_obj.status in ("completed", "failed", "cancelled") else 0,
            current_node=None,
            error=exec_obj.error_message if exec_obj.status == "failed" else None,
        )
    except WorkflowExecution.DoesNotExist:
        return ProgressSchema(status="not_found", progress=0, error="Execution not found")
