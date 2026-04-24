"""
Celery Tasks — Phase 9: Async Task Queue

Background tasks for long-running operations:
- Workflow execution offloaded to workers
- Document processing (chunking + embedding)
- Periodic maintenance tasks
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Optional

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─── Workflow Execution ────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def run_workflow_task(
    self,
    execution_id: int,
    workflow_id: int,
    thread_id: str,
    user_query: str,
    context: Optional[dict[str, Any]] = None,
    model_name: str = "doubao",
    parallel_branches: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Execute a workflow in the background via Celery.

    This offloads the entire LangGraph execution from the HTTP request thread,
    enabling:
    - Long-running workflows without request timeouts
    - Task cancellation via /api/tasks/{task_id}/cancel
    - Progress tracking via Django Cache
    - Scheduled/periodic workflows

    Args:
        execution_id: Database ID of the WorkflowExecution record.
        workflow_id: Target workflow ID.
        thread_id: LangGraph thread ID (UUID string).
        user_query: The user's query/prompt.
        context: Optional additional context dict.
        model_name: LLM model to use.
        parallel_branches: Optional explicit parallel branch list.

    Returns:
        Dict with status and execution metadata.
    """
    from ai_engine.models import WorkflowExecution
    from django.core.cache import cache

    task_id = self.request.id
    cache_key = f"workflow_progress:{execution_id}"

    try:
        # ── Update execution to running ────────────────────────────────────
        execution = WorkflowExecution.objects.get(id=execution_id)
        execution.status = "running"
        execution.started_at = timezone.now()
        execution.save(update_fields=["status", "started_at"])

        cache.set(
            cache_key,
            {"status": "running", "progress": 0, "current_node": "router"},
            timeout=7200,
        )

        # ── Run the workflow ────────────────────────────────────────────────
        raw_in = execution.input_data or {}
        client_node_id = str(raw_in.get("client_node_id") or "")
        model_eff = raw_in.get("model_name")
        if isinstance(model_eff, str) and model_eff.strip():
            model_name = model_eff.strip()
        branches_raw = raw_in.get("parallel_branches")
        if isinstance(branches_raw, list):
            parallel_branches = branches_raw
        force_g = bool(raw_in.get("force_general_assistant"))
        model_key_celery = str(raw_in.get("model_key") or "")
        ru = raw_in.get("runtime_user_id_for_catalog")
        runtime_uid: int | None = None
        if ru is not None and str(ru).strip().isdigit():
            runtime_uid = int(str(ru).strip())

        async def _run():
            # Import here to avoid circular imports and to get fresh event loop
            from ai_engine.api import _run_workflow_async
            await _run_workflow_async(
                execution_id=execution_id,
                thread_id=thread_id,
                workflow_id=workflow_id,
                query=user_query,
                context=context or {},
                model_name=model_name,
                parallel_branches=parallel_branches,
                client_node_id=client_node_id,
                force_general_assistant=force_g,
                model_key=model_key_celery,
                runtime_user_id=runtime_uid,
            )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()

        # ── Mark complete ──────────────────────────────────────────────────
        execution.refresh_from_db()
        execution.status = "completed"
        execution.completed_at = timezone.now()
        execution.save(update_fields=["status", "completed_at"])

        cache.set(
            cache_key,
            {"status": "completed", "progress": 100, "current_node": "finalize"},
            timeout=3600,
        )

        return {
            "status": "completed",
            "execution_id": execution_id,
            "task_id": task_id,
        }

    except SoftTimeLimitExceeded:
        _mark_failed(execution_id, "Task timed out (soft limit exceeded)")
        raise

    except Exception as exc:
        _mark_failed(execution_id, str(exc))
        logger.exception(f"Workflow task {task_id} failed: {exc}")
        raise self.retry(exc=exc)


def _mark_failed(execution_id: int, error_message: str) -> None:
    """Helper: mark an execution as failed in the database."""
    from ai_engine.models import WorkflowExecution
    from django.core.cache import cache

    try:
        WorkflowExecution.objects.filter(id=execution_id).update(
            status="failed",
            error_message=error_message,
            completed_at=timezone.now(),
        )
        cache.set(
            f"workflow_progress:{execution_id}",
            {"status": "failed", "error": error_message},
            timeout=3600,
        )
    except Exception:
        pass


@shared_task(bind=True, max_retries=0)
def cancel_workflow_task(
    self,
    execution_id: int,
    task_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Cancel a running workflow task.

    Revokes the Celery task and marks the execution as cancelled.
    Note: Cancellation is best-effort; the task may still complete if already
    past the cancellation checkpoint.
    """
    from ai_engine.models import WorkflowExecution
    from django.core.cache import cache

    # Revoke the task
    if task_id:
        self.app.control.revoke(task_id, terminate=True)

    # Mark execution cancelled
    try:
        WorkflowExecution.objects.filter(id=execution_id).update(
            status="cancelled",
            error_message="Cancelled by user",
            completed_at=timezone.now(),
        )
        cache.set(
            f"workflow_progress:{execution_id}",
            {"status": "cancelled"},
            timeout=3600,
        )
    except Exception:
        pass

    return {"cancelled": True, "execution_id": execution_id}


# ─── Document Processing ──────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=120, autoretry_for=(Exception,))
def process_document_task(self, document_id: int) -> dict[str, Any]:
    """
    Process a document: extract text, chunk, and embed into the vector store.

    Runs in a dedicated 'documents' queue to avoid blocking workflow execution.
    """
    from ai_engine.rag_api import _do_process_document

    try:
        _do_process_document(document_id)
        return {
            "status": "completed",
            "document_id": document_id,
        }
    except Exception as exc:
        logger.exception(f"Document processing failed for {document_id}: {exc}")
        raise self.retry(exc=exc)


# ─── AI 自动回复（默认走 workflows 队列，与现有 Celery worker 兼容；失败已在 DB 标记）──

@shared_task(name="ai_engine.tasks.run_auto_reply_job_task")
def run_auto_reply_job_task(job_id: int) -> dict[str, Any]:
    """执行一条 AutoReplyJob（数据库读写 + LLM 调用）。"""
    from ai_engine.auto_reply.runner import run_auto_reply_job_sync

    run_auto_reply_job_sync(int(job_id))
    return {"status": "ok", "job_id": job_id}


# ─── Maintenance Tasks ────────────────────────────────────────────────────────

@shared_task(name="ai_engine.tasks.cleanup_failed_executions")
def cleanup_failed_executions(days: int = 7) -> str:
    """
    Delete WorkflowExecution records that have been in 'failed' status
    for more than `days` days.

    Runs daily at 3 AM via Celery Beat.
    """
    from ai_engine.models import WorkflowExecution

    cutoff = timezone.now() - timedelta(days=days)
    deleted_count, _ = WorkflowExecution.objects.filter(
        status="failed",
        completed_at__lt=cutoff,
    ).delete()

    logger.info(f"Cleaned up {deleted_count} failed executions older than {days} days")
    return f"Cleaned up {deleted_count} failed executions"


@shared_task(name="ai_engine.tasks.retry_stale_executions")
def retry_stale_executions(timeout_minutes: int = 30) -> str:
    """
    Find executions stuck in 'running' status and mark them as failed,
    then optionally re-queue them.

    Runs every 5 minutes via Celery Beat.
    """
    from ai_engine.models import WorkflowExecution

    timeout = timezone.now() - timedelta(minutes=timeout_minutes)
    stale_qs = WorkflowExecution.objects.filter(
        status="running",
        started_at__lt=timeout,
    )

    count = stale_qs.count()
    if count == 0:
        return "No stale executions found"

    stale_qs.update(
        status="failed",
        error_message="Execution timed out (worker crashed or exceeded time limit)",
        completed_at=timezone.now(),
    )

    logger.warning(f"Marked {count} stale executions as failed")
    return f"Marked {count} stale executions as failed"


@shared_task(name="ai_engine.tasks.warm_workflow_cache")
def warm_workflow_cache() -> str:
    """
    Pre-warm the LangGraph workflow graph compilation cache.

    LangGraph lazily compiles the StateGraph on first use. This task
    triggers compilation proactively so that the first real request
    doesn't pay the compilation cost.
    """
    from ai_engine.workflow import get_workflow_graph

    try:
        graph = get_workflow_graph()
        # Touch the compiled graph to verify it initializes cleanly
        logger.info(f"Workflow graph cache warmed: {graph}")
        return "Workflow graph cache warmed"
    except Exception as exc:
        logger.error(f"Failed to warm workflow cache: {exc}")
        return f"Failed: {exc}"


# ─── Progress helpers ─────────────────────────────────────────────────────────

@shared_task(name="ai_engine.tasks.update_progress")
def update_progress(
    execution_id: int,
    status: str,
    progress: int,
    current_node: str,
) -> None:
    """
    Update workflow progress in Django Cache.

    Called by the workflow engine nodes to broadcast progress to the frontend
    via WebSocket polling.
    """
    from django.core.cache import cache

    cache.set(
        f"workflow_progress:{execution_id}",
        {"status": status, "progress": progress, "current_node": current_node},
        timeout=7200,
    )
