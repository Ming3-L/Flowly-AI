"""
Async Task API — Phase 9: Celery

Ninja router for Celery task management:
- Submit workflows for async execution
- Query task status
- Cancel running tasks
- Monitor task progress
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from django.http import HttpRequest
from ninja import Router, Schema  # pyright: ignore[reportMissingImports]
from pydantic import Field  # pyright: ignore[reportMissingImports]

from .auth import JWTAuth
from .models import Workflow, WorkflowExecution, Thread


# ─── Schemas ─────────────────────────────────────────────────────────────────

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


# ─── Router ─────────────────────────────────────────────────────────────────

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
    Submit a workflow for async execution via Celery.

    Returns immediately with a task_id. The frontend can:
    - Poll GET /api/tasks/{task_id}/status for status updates
    - Connect to WebSocket /ws/workflow/{thread_id}/ for real-time events
    - Call POST /api/tasks/{task_id}/cancel to abort

    Use this endpoint instead of POST /api/workflows/run when:
    - Workflows may take longer than the HTTP request timeout
    - You need the ability to cancel mid-execution
    - You want scheduled/queued execution
    """
    # Validate workflow
    try:
        workflow = Workflow.objects.get(id=workflow_id, is_active=True)
    except Workflow.DoesNotExist:
        return AsyncRunResponseSchema(
            task_id="",
            execution_id=0,
            thread_id="",
            status="error",
            message=f"Workflow {workflow_id} not found or inactive",
        )

    # Create thread and execution records
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

    # Dispatch to Celery worker
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
        message="Workflow queued for execution",
    )


@router.get("/{task_id}/status", response=TaskStatusSchema)
def get_task_status(request: HttpRequest, task_id: str) -> TaskStatusSchema:
    """
    Query the status of a Celery task.

    Returns: PENDING | STARTED | SUCCESS | FAILURE | REVOKED
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
    Cancel a running or queued Celery task.

    Best-effort: the task may still complete if it passed the cancellation
    checkpoint before this request was processed.
    """
    from celery.result import AsyncResult

    # Revoke the task in Celery
    AsyncResult(task_id).revoke(terminate=True)

    # Update execution record
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

    # Fallback: return DB status
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
