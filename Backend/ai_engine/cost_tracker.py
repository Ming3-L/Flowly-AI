"""
Cost Tracker — Phase 10: Observability

Tracks LLM usage and costs per workflow execution.
Uses a pricing table (updated 2024-2025) for major model providers.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Mapping, Optional

from django.utils import timezone


logger = logging.getLogger(__name__)


def extract_token_usage_from_lc_message(message: Any) -> tuple[int, int]:
    """
    从 LangChain Chat 返回的 AIMessage 上尽量解析 token 用量。

    兼容 ``usage_metadata``（较新）与 ``response_metadata.token_usage``（OpenAI）。
    """
    usage_md = getattr(message, "usage_metadata", None) or {}
    if isinstance(usage_md, dict):
        inp = int(
            usage_md.get("input_tokens")
            or usage_md.get("prompt_tokens")
            or 0
        )
        out = int(
            usage_md.get("output_tokens")
            or usage_md.get("completion_tokens")
            or 0
        )
        if inp or out:
            return inp, out
    meta = getattr(message, "response_metadata", None) or {}
    if not isinstance(meta, dict):
        return 0, 0
    tu = meta.get("token_usage") or meta.get("usage") or {}
    if not isinstance(tu, dict):
        return 0, 0
    inp = int(tu.get("prompt_tokens", tu.get("input_tokens", 0)) or 0)
    out = int(tu.get("completion_tokens", tu.get("output_tokens", 0)) or 0)
    return inp, out


def extract_model_id_from_lc_message(message: Any, fallback: str) -> str:
    """从响应元数据取模型 id，用于计价表匹配。"""
    meta = getattr(message, "response_metadata", None) or {}
    if isinstance(meta, dict):
        name = meta.get("model_name") or meta.get("model")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return fallback


def record_llm_cost_for_workflow_state(
    state: Mapping[str, Any],
    message: Any,
    *,
    logical_node_name: str,
    model_fallback: str,
) -> None:
    """
    在存在 ``_execution_id`` 时写入 ``CostRecord``，并带上 ``_client_node_id``（画布节点）。

    无 execution 或无法解析 token 时直接返回（不写脏数据）。
    """
    execution_id = state.get("_execution_id")
    if not execution_id:
        return
    inp, outp = extract_token_usage_from_lc_message(message)
    if inp == 0 and outp == 0:
        logger.debug(
            "Skipping CostRecord: no token usage on message (check provider/SDK "
            "usage_metadata or response_metadata.token_usage). execution_id=%s node=%s",
            execution_id,
            logical_node_name,
        )
        return
    from ai_engine.models import WorkflowExecution

    ex = (
        WorkflowExecution.objects.filter(pk=int(execution_id))
        .select_related("thread", "workflow")
        .first()
    )
    if not ex:
        return
    model_id = extract_model_id_from_lc_message(message, model_fallback)
    uid = ex.thread.user_id if ex.thread else None
    client = str(state.get("_client_node_id") or "")
    try:
        get_cost_tracker().track(
            model=model_id,
            input_tokens=inp,
            output_tokens=outp,
            execution_id=ex.pk,
            workflow_id=ex.workflow_id,
            user_id=uid,
            node_name=logical_node_name,
            client_node_id=client,
        )
    except Exception:
        logger.exception("CostRecord.track failed for execution_id=%s node=%s", execution_id, logical_node_name)


def record_llm_cost_from_canvas_context(
    execution_id: int | None,
    message: Any,
    *,
    logical_node_name: str,
    model_fallback: str,
    client_node_id: str,
) -> None:
    """供画布单步执行：等价于带伪 state 的 ``record_llm_cost_for_workflow_state``。"""
    if not execution_id:
        return
    record_llm_cost_for_workflow_state(
        {"_execution_id": execution_id, "_client_node_id": client_node_id},
        message,
        logical_node_name=logical_node_name,
        model_fallback=model_fallback,
    )


# ─── Pricing Table (per 1K tokens) ───────────────────────────────────────────

class ModelPricing:
    """
    LLM pricing table in USD per 1,000 tokens.
    Prices sourced from OpenAI, Anthropic, and Ollama (2024-2025).
    """

    PRICING: dict[str, dict[str, float]] = {
        # OpenAI
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.010, "output": 0.030},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "o1-preview": {"input": 0.015, "output": 0.060},
        "o1-mini": {"input": 0.003, "output": 0.012},
        # Anthropic
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        "claude-3-5-sonnet-20240620": {"input": 0.003, "output": 0.015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        # Embeddings
        "text-embedding-3-small": {"input": 0.00002, "output": 0},
        "text-embedding-3-large": {"input": 0.00013, "output": 0},
        "text-embedding-ada-002": {"input": 0.00010, "output": 0},
        # Ollama (local — no API cost)
        "llama3": {"input": 0.000, "output": 0.000},
        "llama3.1": {"input": 0.000, "output": 0.000},
        "mistral": {"input": 0.000, "output": 0.000},
        "mixtral": {"input": 0.000, "output": 0.000},
        # Fallback
        "unknown": {"input": 0.0, "output": 0.0},
    }

    @classmethod
    def get_price(cls, model: str) -> tuple[float, float]:
        """Return (input_price_per_1k, output_price_per_1k) for a model."""
        key = model.lower().strip()
        prices = cls.PRICING.get(key, cls.PRICING["unknown"])

        # Fuzzy match fallback
        if key not in cls.PRICING:
            for known_key, known_prices in cls.PRICING.items():
                if known_key in key:
                    prices = known_prices
                    break

        return prices["input"], prices["output"]


# ─── Cost Tracker ────────────────────────────────────────────────────────────

class CostTracker:
    """
    Tracks LLM usage and costs for workflow executions.

    Usage:
        tracker = CostTracker()
        tracker.track(
            execution_id=123,
            model="gpt-4o",
            input_tokens=500,
            output_tokens=200,
            latency_ms=1200,
            node_name="router",
        )
    """

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Calculate the USD cost for a given token count.
        Returns (input_cost, output_cost, total_cost) as Decimal.
        """
        input_price, output_price = ModelPricing.get_price(model)
        input_cost = Decimal(str(input_tokens)) * Decimal(str(input_price)) / Decimal("1000")
        output_cost = Decimal(str(output_tokens)) * Decimal(str(output_price)) / Decimal("1000")
        return input_cost, output_cost, input_cost + output_cost

    def track(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int = 0,
        execution_id: int | None = None,
        workflow_id: int | None = None,
        user_id: int | None = None,
        node_name: str = "",
        call_type: str = "completion",
        client_node_id: str = "",
        conversation_session_id: int | None = None,
    ) -> Any:
        """
        Record a LLM call's token usage and cost to the database.
        Returns the created CostRecord instance.

        ``client_node_id`` 与画布 ``WorkflowGraphNode.client_node_id`` 对齐；
        ``conversation_session_id`` 供未来按会话聚合（自动回复等）。
        """
        input_cost, output_cost, total_cost = self.calculate_cost(
            model, input_tokens, output_tokens
        )
        provider = self._detect_provider(model)

        return self._create_record(
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            latency_ms=latency_ms,
            execution_id=execution_id,
            workflow_id=workflow_id,
            user_id=user_id,
            node_name=node_name,
            call_type=call_type,
            client_node_id=client_node_id,
            conversation_session_id=conversation_session_id,
        )

    def _create_record(self, **kwargs) -> Any:
        """Create a CostRecord in the database."""
        from .analytics_models import CostRecord
        record = CostRecord(**kwargs)
        record.total_tokens = record.input_tokens + record.output_tokens
        record.save()
        return record

    def _detect_provider(self, model: str) -> str:
        """Detect LLM provider from model name."""
        m = model.lower()
        if "claude" in m or "anthropic" in m:
            return "anthropic"
        if "ollama" in m or "llama" in m or "mistral" in m:
            return "ollama"
        if "codex" in m or "vectorengine" in m:
            return "vectorengine"
        return "openai"

    def get_workflow_costs(
        self,
        workflow_id: int,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Get total costs for a workflow in a date range."""
        from .analytics_models import CostRecord

        qs = CostRecord.objects.filter(
            workflow_id=workflow_id,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        return {
            "total_cost_usd": float(sum(r.total_cost_usd for r in qs)),
            "total_input_tokens": sum(r.input_tokens for r in qs),
            "total_output_tokens": sum(r.output_tokens for r in qs),
            "total_calls": qs.count(),
        }

    def get_model_breakdown(
        self,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Get cost breakdown by model."""
        from .analytics_models import CostRecord
        from django.db.models import Sum, Count

        breakdown = (
            CostRecord.objects.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )
            .values("model", "provider")
            .annotate(
                total_cost=Sum("total_cost_usd"),
                total_input_tokens=Sum("input_tokens"),
                total_output_tokens=Sum("output_tokens"),
                total_calls=Count("id"),
            )
            .order_by("-total_cost")
        )
        return [
            {
                "model": row["model"],
                "provider": row["provider"],
                "total_cost_usd": float(row["total_cost"]),
                "total_input_tokens": row["total_input_tokens"] or 0,
                "total_output_tokens": row["total_output_tokens"] or 0,
                "total_calls": row["total_calls"],
            }
            for row in breakdown
        ]


_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get the singleton CostTracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
