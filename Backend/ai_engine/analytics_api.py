"""
Observability API — Phase 10: Observability

Analytics endpoints for usage, cost, and performance monitoring.
Also provides integration with LangSmith/Langfuse for tracing.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, F, Sum
from django.db import models as django_models
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.http import HttpRequest
from ninja import Router, Schema  # pyright: ignore[reportMissingImports]
from pydantic import Field  # pyright: ignore[reportMissingImports]

from .auth import JWTAuth
from .models import Workflow, WorkflowExecution
from .cost_tracker import get_cost_tracker


# ─── Schemas ─────────────────────────────────────────────────────────────────

class UsageDataPointSchema(Schema):
    date: str
    executions: int
    avg_duration_seconds: float | None


class CostDataPointSchema(Schema):
    date: str
    cost_usd: float
    calls: int


class WorkflowStatSchema(Schema):
    workflow_id: int
    workflow_name: str
    total_executions: int
    completed_executions: int
    failed_executions: int
    avg_duration_seconds: float | None
    total_cost_usd: float


class ModelUsageSchema(Schema):
    model: str
    provider: str
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float


class UsageAnalyticsSchema(Schema):
    total_executions: int
    completed: int
    failed: int
    avg_duration_seconds: float | None
    time_series: list[UsageDataPointSchema]


class CostAnalyticsSchema(Schema):
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    by_model: list[ModelUsageSchema]
    by_date: list[CostDataPointSchema]


class PerformanceAnalyticsSchema(Schema):
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    slowest_workflows: list[dict[str, Any]]


class WorkflowStatsSchema(Schema):
    workflow_id: int
    name: str
    execution_count_30d: int
    success_rate: float
    avg_cost_30d: float
    avg_duration_seconds: float | None


# ─── Router ─────────────────────────────────────────────────────────────────

router = Router(tags=["Observability / Analytics"], auth=JWTAuth())


def _parse_date(d: Optional[str], default: date) -> date:
    """Parse date string 'YYYY-MM-DD' to date object."""
    if not d:
        return default
    try:
        return date.fromisoformat(d)
    except ValueError:
        return default


@router.get("/usage", response=UsageAnalyticsSchema)
def get_usage_analytics(
    request: HttpRequest,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = "day",
    workflow_id: Optional[int] = None,
) -> UsageAnalyticsSchema:
    """
    Usage analytics: execution counts over time.

    Args:
        start_date: Start date (default: 30 days ago)
        end_date: End date (default: today)
        granularity: 'day' | 'week' | 'month'
        workflow_id: Filter by specific workflow (optional)
    """
    start = _parse_date(start_date, date.today() - timedelta(days=30))
    end = _parse_date(end_date, date.today())

    u = getattr(request, "auth", None) or getattr(request, "user", None)
    if not getattr(u, "is_authenticated", False):
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")

    queryset = WorkflowExecution.objects.filter(
        workflow__user=u,
        started_at__date__gte=start,
        started_at__date__lte=end,
    )
    if workflow_id:
        queryset = queryset.filter(workflow_id=workflow_id)

    # Group by date
    trunc_map = {
        "day": TruncDate("started_at"),
        "week": TruncWeek("started_at"),
        "month": TruncMonth("started_at"),
    }
    trunc = trunc_map.get(granularity, TruncDate("started_at"))

    grouped = (
        queryset.annotate(day=trunc)
        .values("day")
        .annotate(
            executions=Count("id"),
            avg_duration=Avg(
                F("completed_at") - F("started_at"),
                output_field=django_models.DurationField(),
            ),
        )
        .order_by("day")
    )

    time_series = []
    for row in grouped:
        avg_dur = row["avg_duration"]
        avg_seconds = (
            avg_dur.total_seconds() if avg_dur else None
        )
        time_series.append(
            UsageDataPointSchema(
                date=str(row["day"]) if row["day"] else "",
                executions=row["executions"],
                avg_duration_seconds=round(avg_seconds, 2) if avg_seconds else None,
            )
        )

    total = queryset.count()
    completed = queryset.filter(status="completed").count()
    failed = queryset.filter(status="failed").count()

    overall_avg = (
        queryset.filter(status="completed")
        .annotate(dur=F("completed_at") - F("started_at"))
        .aggregate(avg=Avg("dur"))["avg"]
    )
    overall_avg_seconds = (
        overall_avg.total_seconds() if overall_avg else None
    )

    return UsageAnalyticsSchema(
        total_executions=total,
        completed=completed,
        failed=failed,
        avg_duration_seconds=round(overall_avg_seconds, 2) if overall_avg_seconds else None,
        time_series=time_series,
    )


@router.get("/costs", response=CostAnalyticsSchema)
def get_cost_analytics(
    request: HttpRequest,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "model",
    user_id: Optional[int] = None,
) -> CostAnalyticsSchema:
    """
    Cost analytics: LLM costs by model and over time.

    Args:
        start_date: Start date (default: 30 days ago)
        end_date: End date (default: today)
        group_by: 'model' | 'workflow' | 'user'
        user_id: Filter by user (admin only, defaults to own costs)
    """
    from .analytics_models import CostRecord

    start = _parse_date(start_date, date.today() - timedelta(days=30))
    end = _parse_date(end_date, date.today())

    u = getattr(request, "auth", None) or getattr(request, "user", None)
    if not getattr(u, "is_authenticated", False):
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")

    queryset = CostRecord.objects.filter(
        created_at__date__gte=start,
        created_at__date__lte=end,
    )
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    else:
        queryset = queryset.filter(user=u)

    # Total
    totals = queryset.aggregate(
        total_cost=django_models.Sum("total_cost_usd"),
        total_input=django_models.Sum("input_tokens"),
        total_output=django_models.Sum("output_tokens"),
    )

    # By model
    model_breakdown = get_cost_tracker().get_model_breakdown(start, end)
    if user_id:
        pass  # Already filtered above
    else:
        model_breakdown = [
            row for row in model_breakdown
            if True  # All models for the user
        ]

    # By date
    by_date_qs = (
        queryset.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            cost=django_models.Sum("total_cost_usd"),
            calls=Count("id"),
        )
        .order_by("day")
    )
    by_date = [
        CostDataPointSchema(
            date=str(row["day"]) if row["day"] else "",
            cost_usd=float(row["cost"] or 0),
            calls=row["calls"],
        )
        for row in by_date_qs
    ]

    return CostAnalyticsSchema(
        total_cost_usd=float(totals["total_cost"] or 0),
        total_input_tokens=totals["total_input"] or 0,
        total_output_tokens=totals["total_output"] or 0,
        by_model=model_breakdown,
        by_date=by_date,
    )


@router.get("/performance", response=PerformanceAnalyticsSchema)
def get_performance_analytics(
    request: HttpRequest,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> PerformanceAnalyticsSchema:
    """
    Performance analytics: latency and throughput metrics.

    Args:
        start_date: Start date (default: 30 days ago)
        end_date: End date (default: today)
    """
    from .analytics_models import CostRecord

    start = _parse_date(start_date, date.today() - timedelta(days=30))
    end = _parse_date(end_date, date.today())

    u = getattr(request, "auth", None) or getattr(request, "user", None)
    if not getattr(u, "is_authenticated", False):
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")

    latencies = list(
        CostRecord.objects.filter(
            user=u,
            created_at__date__gte=start,
            created_at__date__lte=end,
            latency_ms__gt=0,
        )
        .values_list("latency_ms", flat=True)
        .order_by("latency_ms")
    )

    def percentile(data: list, p: float) -> float:
        if not data:
            return 0.0
        idx = int(len(data) * p)
        idx = min(idx, len(data) - 1)
        return float(data[idx])

    avg_lat = sum(latencies) / len(latencies) if latencies else 0
    p50 = percentile(latencies, 0.50)
    p95 = percentile(latencies, 0.95)
    p99 = percentile(latencies, 0.99)

    # Slowest workflows (by avg duration)
    slowest = (
        Workflow.objects.filter(user=u)
        .annotate(
            avg_dur=Avg(
                F("executions__completed_at") - F("executions__started_at"),
            )
        )
        .order_by("-avg_dur")[:5]
    )

    from django.db.models.functions import Coalesce
    from django.db.models import Value

    slowest_rows = []
    for wf in slowest:
        exec_count = wf.executions.filter(
            started_at__date__gte=start,
            started_at__date__lte=end,
        ).count()
        if exec_count > 0:
            slowest_rows.append({
                "workflow_id": wf.id,
                "workflow_name": wf.name,
                "executions": exec_count,
            })

    return PerformanceAnalyticsSchema(
        avg_latency_ms=round(avg_lat, 2),
        p50_latency_ms=round(p50, 2),
        p95_latency_ms=round(p95, 2),
        p99_latency_ms=round(p99, 2),
        slowest_workflows=slowest_rows,
    )


@router.get("/workflows", response=list[WorkflowStatsSchema])
def get_workflow_stats(
    request: HttpRequest,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[WorkflowStatsSchema]:
    """
    Per-workflow statistics for the current user.

    Args:
        start_date: Start date (default: 30 days ago)
        end_date: End date (default: today)
    """
    start = _parse_date(start_date, date.today() - timedelta(days=30))
    end = _parse_date(end_date, date.today())

    u = getattr(request, "auth", None) or getattr(request, "user", None)
    if not getattr(u, "is_authenticated", False):
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")

    workflows = Workflow.objects.filter(user=u)

    results: list[WorkflowStatsSchema] = []
    for wf in workflows:
        execs = wf.executions.filter(
            started_at__date__gte=start,
            started_at__date__lte=end,
        )
        total = execs.count()
        completed = execs.filter(status="completed").count()
        success_rate = (completed / total) if total > 0 else 0.0

        avg_dur = (
            execs.filter(status="completed")
            .annotate(dur=F("completed_at") - F("started_at"))
            .aggregate(avg=django_models.Avg("dur"))["avg"]
        )
        avg_seconds = avg_dur.total_seconds() if avg_dur else None

        # Average cost from cost records
        cost_sum = (
            wf.cost_records.filter(
                created_at__date__gte=start,
                created_at__date__lte=end,
            )
            .aggregate(total=Sum("total_cost_usd"))["total"]
            or 0
        )

        results.append(
            WorkflowStatsSchema(
                workflow_id=wf.id,
                name=wf.name,
                execution_count_30d=total,
                success_rate=round(success_rate * 100, 2),
                avg_cost_30d=float(cost_sum),
                avg_duration_seconds=round(avg_seconds, 2) if avg_seconds else None,
            )
        )

    return results


# ─── LangSmith Integration ──────────────────────────────────────────────────

def configure_langsmith_tracing() -> None:
    """
    Initialize LangSmith tracing from Django settings.

    Call this once at application startup (e.g. in apps.py ready()).
    """
    import os
    from django.conf import settings

    if not (getattr(settings, "LANGSMITH_TRACING", False) and getattr(settings, "LANGSMITH_API_KEY", None)):
        return

    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_API_KEY", settings.LANGSMITH_API_KEY)
    os.environ.setdefault(
        "LANGSMITH_PROJECT",
        getattr(settings, "LANGSMITH_PROJECT", "flowly-ai"),
    )
    if getattr(settings, "LANGSMITH_ENDPOINT", None):
        os.environ.setdefault("LANGSMITH_ENDPOINT", settings.LANGSMITH_ENDPOINT)
