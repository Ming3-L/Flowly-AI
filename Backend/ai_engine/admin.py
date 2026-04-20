from django.contrib import admin

from .models import Workflow, Thread, WorkflowExecution
from .rag_models import Document
from .analytics_models import CostRecord


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    """Admin configuration for Workflow model."""
    list_display = ["id", "name", "is_active", "created_at", "updated_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = [
        ("Basic Info", {"fields": ["name", "description", "is_active"]}),
        ("Definition", {"fields": ["definition"], "classes": ["collapse"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    """Admin configuration for Thread model."""
    list_display = ["id", "thread_id", "workflow", "user", "created_at", "updated_at"]
    list_filter = ["workflow", "created_at"]
    search_fields = ["thread_id"]
    readonly_fields = ["thread_id", "created_at", "updated_at"]
    ordering = ["-created_at"]
    raw_id_fields = ["user", "workflow"]


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowExecution model."""
    list_display = [
        "id", "workflow", "status", "started_at", "completed_at"
    ]
    list_filter = ["status", "workflow", "started_at"]
    search_fields = ["thread__thread_id"]
    readonly_fields = ["started_at", "completed_at"]
    ordering = ["-started_at"]
    raw_id_fields = ["workflow", "thread"]

    fieldsets = [
        ("Execution Info", {"fields": ["workflow", "thread", "status"]}),
        ("Data", {"fields": ["input_data", "output_data", "error_message"]}),
        ("Timing", {"fields": ["started_at", "completed_at"]}),
    ]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin for knowledge base documents (Phase 8: RAG)."""
    list_display = ["id", "filename", "workflow", "file_type", "processing_status", "chunk_count", "created_at"]
    list_filter = ["processing_status", "file_type", "workflow"]
    search_fields = ["filename", "title"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(CostRecord)
class CostRecordAdmin(admin.ModelAdmin):
    """Admin for LLM cost tracking (Phase 10: Observability)."""
    list_display = ["id", "model", "provider", "input_tokens", "output_tokens", "total_cost_usd", "created_at"]
    list_filter = ["provider", "model", "created_at"]
    search_fields = ["model", "workflow__name"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]

