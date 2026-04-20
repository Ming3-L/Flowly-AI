"""
Execution History API — list, retrieve, statistics.

All endpoints require JWT authentication via HttpBearer.
"""

from django.db.models import Count, Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Query, Router, Schema  # pyright: ignore[reportMissingImports]

from .auth import JWTAuth
from .models import Workflow, WorkflowExecution, Thread

exec_router = Router(tags=["Executions"], auth=JWTAuth())


class ExecutionResponseSchema(Schema):
    id: int
    workflow_id: int
    workflow_name: str
    thread_id: str
    status: str
    input_data: dict
    output_data: dict
    error_message: str
    started_at: str
    completed_at: str | None
    duration_seconds: float | None = None


class ExecutionListSchema(Schema):
    total: int
    items: list[ExecutionResponseSchema]


class ExecutionStatsSchema(Schema):
    total_executions: int
    completed: int
    running: int
    pending: int
    failed: int
    avg_duration_seconds: float | None


class MessageSchema(Schema):
    message: str
    detail: str | None = None


def _execution_to_response(exec: WorkflowExecution) -> ExecutionResponseSchema:
    """Convert WorkflowExecution model to response schema."""
    duration = None
    if exec.started_at and exec.completed_at:
        delta = exec.completed_at - exec.started_at
        duration = delta.total_seconds()

    return ExecutionResponseSchema(
        id=exec.id,
        workflow_id=exec.workflow_id,
        workflow_name=exec.workflow.name if exec.workflow else "Unknown",
        thread_id=str(exec.thread.thread_id) if exec.thread else "",
        status=exec.status,
        input_data=exec.input_data or {},
        output_data=exec.output_data or {},
        error_message=exec.error_message or "",
        started_at=exec.started_at.isoformat() if exec.started_at else "",
        completed_at=exec.completed_at.isoformat() if exec.completed_at else None,
        duration_seconds=round(duration, 2) if duration is not None else None,
    )


@exec_router.get("/", response=ExecutionListSchema)
def list_executions(
    request: HttpRequest,
    workflow_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """
    GET /api/executions/

    List workflow executions for the authenticated user.
    """
    queryset = WorkflowExecution.objects.filter(
        workflow__user=request.user
    ).select_related("workflow", "thread")

    if workflow_id is not None:
        queryset = queryset.filter(workflow_id=workflow_id)

    if status:
        queryset = queryset.filter(status=status)

    total = queryset.count()
    items = [
        _execution_to_response(e)
        for e in queryset.order_by("-started_at")[offset:offset + limit]
    ]

    return ExecutionListSchema(total=total, items=items)


@exec_router.get("/stats", response=ExecutionStatsSchema)
def execution_stats(request: HttpRequest, workflow_id: int | None = None):
    """
    GET /api/executions/stats

    Return aggregated execution statistics for the authenticated user.
    """
    queryset = WorkflowExecution.objects.filter(workflow__user=request.user)

    if workflow_id is not None:
        queryset = queryset.filter(workflow_id=workflow_id)

    stats = queryset.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status="completed")),
        running=Count("id", filter=Q(status="running")),
        pending=Count("id", filter=Q(status="pending")),
        failed=Count("id", filter=Q(status="failed")),
    )

    return ExecutionStatsSchema(
        total_executions=stats["total"],
        completed=stats["completed"],
        running=stats["running"],
        pending=stats["pending"],
        failed=stats["failed"],
        avg_duration_seconds=None,
    )


@exec_router.get("/{execution_id}", response={200: ExecutionResponseSchema, 404: MessageSchema})
def get_execution(request: HttpRequest, execution_id: int):
    """
    GET /api/executions/{id}

    Retrieve a single execution by ID.
    """
    exec_obj = get_object_or_404(
        WorkflowExecution.objects.select_related("workflow", "thread"),
        id=execution_id,
        workflow__user=request.user,
    )
    return 200, _execution_to_response(exec_obj)
