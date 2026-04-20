from django.contrib.auth.models import User
from django.db import models


# ─────────────────────────────────────────────────────────────────────────────
# AI Engine Models
# ─────────────────────────────────────────────────────────────────────────────

class Workflow(models.Model):
    """Represents an AI workflow definition."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="flowly_workflows",
        null=True,
        blank=True,
        help_text="Owner of this workflow (null for system/global workflows)",
    )
    name = models.CharField(max_length=255, help_text="Workflow name")
    description = models.TextField(blank=True, help_text="Workflow description")
    definition = models.JSONField(help_text="Workflow definition in JSON format")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Thread(models.Model):
    """
    Tracks a single workflow session (thread).

    One user can have many threads; each thread is tied to exactly one workflow.
    The thread_id (UUID) is the primary handle used by LangGraph's checkpointer
    to persist and resume state.
    """

    thread_id = models.UUIDField(
        unique=True,
        editable=False,
        help_text="Unique thread ID used by LangGraph checkpointer",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="flowly_threads",
        null=True,
        blank=True,
        help_text="Owner of this thread (null for anonymous sessions)",
    )
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="threads",
        help_text="Workflow definition this thread uses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Threads"

    def __str__(self):
        user_str = self.user.username if self.user else "anonymous"
        return f"{self.workflow.name} / {self.thread_id} ({user_str})"


class WorkflowExecution(models.Model):
    """Represents a single execution of a workflow."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='executions')
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name='executions',
        null=True,
        blank=True,
        help_text="Parent thread for this execution",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name_plural = "Workflow executions"

    def __str__(self):
        return f"{self.workflow.name} - {self.thread_id}"

    @property
    def thread_id(self) -> str:
        """Returns the UUID string of the parent Thread (for backward compatibility)."""
        return str(self.thread.thread_id) if self.thread else ""

