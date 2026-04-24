"""
Analytics Models — Phase 10: Observability

Django models for cost tracking and analytics.
"""

from django.contrib.auth.models import User
from django.db import models


class CostRecord(models.Model):
    """
    Records each LLM call with token usage and computed cost.

    Created automatically by the cost tracker and aggregated via Analytics API.
    """

    execution = models.ForeignKey(
        "ai_engine.WorkflowExecution",
        on_delete=models.CASCADE,
        related_name="cost_records",
        null=True,
        blank=True,
    )
    workflow = models.ForeignKey(
        "ai_engine.Workflow",
        on_delete=models.CASCADE,
        related_name="cost_records",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    model = models.CharField(max_length=100)
    provider = models.CharField(max_length=20, default="openai")

    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)

    input_cost_usd = models.DecimalField(
        max_digits=10, decimal_places=6, default=0
    )
    output_cost_usd = models.DecimalField(
        max_digits=10, decimal_places=6, default=0
    )
    total_cost_usd = models.DecimalField(
        max_digits=10, decimal_places=6, default=0
    )

    node_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="LangGraph 逻辑节点名；与 client_node_id 可同时使用。",
    )

    client_node_id = models.CharField(
        "画布节点 ID",
        max_length=128,
        blank=True,
        default="",
        help_text="与 ``WorkflowGraphNode.client_node_id`` 对齐，用于按画布节点聚合费用。",
    )

    conversation_session = models.ForeignKey(
        "ai_engine.ConversationSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cost_records",
        verbose_name="对话会话",
        help_text="自动回复等场景按会话计费时填写；可与 execution 并存。",
    )

    call_type = models.CharField(max_length=50, default="completion")
    latency_ms = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workflow", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["model", "created_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["conversation_session", "created_at"]),
            models.Index(fields=["workflow", "client_node_id", "created_at"]),
        ]

    def __str__(self):
        return f"{self.model} — {self.total_tokens} tokens — ${self.total_cost_usd}"
