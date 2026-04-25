"""
Celery Application — Phase 9: Async Task Queue

Celery app configuration for background task processing:
- Workflow execution offloaded to Celery workers
- Periodic tasks (cleanup, retry)
- Redis as broker (already deployed)

Usage:
  # Start worker:
  celery -A flowly_backend worker --loglevel=info --concurrency=4

  # Start beat scheduler:
  celery -A flowly_backend beat --loglevel=info

  # Or combined (for development):
  celery -A flowly_backend worker --loglevel=info
"""

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

# ─── Broker / Backend config ────────────────────────────────────────────────────

_broker_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL", "redis://redis:6379/1")
_result_backend = os.getenv("CELERY_RESULT_BACKEND") or os.getenv("REDIS_URL", "redis://redis:6379/1")

app = Celery("flowly_backend")

# Load config from Django settings (namespace CELERY_*)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# ─── Periodic Tasks (Beat) ────────────────────────────────────────────────────

app.conf.beat_schedule = {
    # Clean up failed executions older than 7 days — runs daily at 3 AM
    "cleanup-failed-executions": {
        "task": "ai_engine.tasks.cleanup_failed_executions",
        "schedule": crontab(hour=3, minute=0),
    },
    # Retry executions stuck in "running" for > 30 minutes — runs every 5 minutes
    "retry-stale-executions": {
        "task": "ai_engine.tasks.retry_stale_executions",
        "schedule": 300.0,  # seconds
    },
    # Warm up the workflow graph cache — runs every 30 minutes
    "warm-workflow-cache": {
        "task": "ai_engine.tasks.warm_workflow_cache",
        "schedule": 1800.0,
    },
    # Clean up generated local media older than 90 days — runs daily at 4:10 AM
    "cleanup-generated-media-assets": {
        "task": "ai_engine.tasks.cleanup_generated_media_assets",
        "schedule": crontab(hour=4, minute=10),
        "args": (90, False),
    },
}

# ─── Task routing ─────────────────────────────────────────────────────────────

app.conf.task_routes = {
    "ai_engine.tasks.run_workflow_task": {"queue": "workflows"},
    "ai_engine.tasks.process_document_task": {"queue": "documents"},
    # 可与 workflows 共用队列，避免未单独起 auto_reply worker 时任务积压；生产可改为 "auto_reply"。
    "ai_engine.tasks.run_auto_reply_job_task": {"queue": "workflows"},
    "ai_engine.tasks.cleanup_failed_executions": {"queue": "maintenance"},
    "ai_engine.tasks.retry_stale_executions": {"queue": "maintenance"},
    "ai_engine.tasks.warm_workflow_cache": {"queue": "maintenance"},
    "ai_engine.tasks.cleanup_generated_media_assets": {"queue": "maintenance"},
}

# ─── Task settings ───────────────────────────────────────────────────────────

app.conf.task_acks_late = True          # Acknowledge after task completes (not on receipt)
app.conf.task_reject_on_worker_lost = True
app.conf.task_time_limit = 3600         # Hard limit: 1 hour per task
app.conf.task_soft_time_limit = 1800   # Soft limit: 30 minutes, then warning

# ─── Worker settings ──────────────────────────────────────────────────────────

app.conf.worker_prefetch_multiplier = 1   # One task per worker at a time (for long workflows)
app.conf.worker_concurrency = int(os.getenv("CELERY_WORKER_CONCURRENCY", "4"))

# ─── Result expiration ─────────────────────────────────────────────────────────

app.conf.result_expires = 86400  # Task results expire after 24 hours

# ─── Serialization ───────────────────────────────────────────────────────────

app.conf.accept_content = ["json"]
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.date_parser = "json"

# ─── Health check task ───────────────────────────────────────────────────────

@app.task(bind=True, name="health_check")
def health_check(self):
    """Lightweight task to verify Celery is responding."""
    return {"status": "ok", "worker": self.request.hostname}


@app.task(bind=True, name="flowly.ping")
def ping(self):
    """Ping task for connectivity testing."""
    return "pong"
