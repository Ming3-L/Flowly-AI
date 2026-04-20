"""
Flowly AI Assistant — Custom Assistant using django-ai-assistant

This module provides a custom AIAssistant subclass for Flowly.

**Usage (optional):**
If you prefer to use django-ai-assistant's pre-built models and API views:

1. Uncomment django-ai-assistant in requirements.txt and install it:
   pip install django-ai-assistant[openai]

2. Add to INSTALLED_APPS in settings.py:
   INSTALLED_APPS = [
       ...
       'django_ai_assistant',   # add this
   ]

3. Run migrations:
   python manage.py migrate

4. Remove the custom Thread model from ai_engine/models.py
   (django-ai-assistant provides its own Thread + Message models).

5. Use this file to define custom tools.

The assistant below uses @method_tool to expose Django ORM operations
and other server-side capabilities as LLM-callable tools.
"""

from __future__ import annotations

import json
from typing import Sequence

from django_ai_assistant import AIAssistant, method_tool
from django_ai_assistant.types import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# Tool Input Schemas
# ─────────────────────────────────────────────────────────────────────────────

class SearchWorkflowsInput(BaseModel):
    query: str = Field(description="Search keyword for workflow name or description")


class GetWorkflowDefinitionInput(BaseModel):
    workflow_id: int = Field(description="ID of the workflow to retrieve")


class ListRecentExecutionsInput(BaseModel):
    limit: int = Field(default=5, description="Maximum number of executions to return")


# ─────────────────────────────────────────────────────────────────────────────
# Flowly Assistant
# ─────────────────────────────────────────────────────────────────────────────

class FlowlyAssistant(AIAssistant):
    """
    Custom AI assistant for the Flowly workflow system.

    Exposes Django ORM tools (workflow lookup, execution history) and
    generic utilities as LLM-callable tools via @method_tool.

    Usage in views or management commands::

        from ai_engine.ai_assistants import FlowlyAssistant

        assistant = FlowlyAssistant(user=request.user)
        result = assistant.run("List my recent workflow executions")

    """

    id = "flowly_assistant"  # noqa: A003
    name = "Flowly AI Assistant"
    instructions = (
        "You are Flowly's AI assistant. You help users manage and run "
        "AI-powered workflows. You have access to tools that let you query "
        "workflow definitions, list recent executions, and perform other "
        "Django ORM operations on behalf of the user."
    )
    model = "gpt-4o"

    # ── Overrides ───────────────────────────────────────────────────────────

    def get_instructions(self) -> str:
        """Append dynamic context such as the current date/time."""
        from django.utils import timezone

        base = super().get_instructions()
        return f"{base}\n\nCurrent time: {timezone.now().isoformat()}"

    # ── Tool: Search workflows ──────────────────────────────────────────────

    @method_tool(args_schema=SearchWorkflowsInput)
    def search_workflows(self, query: str) -> str:
        """
        Search workflows by name or description.

        Returns a JSON list of matching workflow objects.
        """
        from ai_engine.models import Workflow

        results = Workflow.objects.filter(
            name__icontains=query,
            is_active=True,
        )[:10]

        data = [
            {
                "id": wf.id,
                "name": wf.name,
                "description": wf.description or "",
                "is_active": wf.is_active,
            }
            for wf in results
        ]
        return json.dumps({"workflows": data, "count": len(data)})

    # ── Tool: Get workflow definition ─────────────────────────────────────

    @method_tool(args_schema=GetWorkflowDefinitionInput)
    def get_workflow_definition(self, workflow_id: int) -> str:
        """
        Retrieve the full definition (LangGraph config) of a workflow by ID.

        Returns a JSON object with workflow metadata and its definition field.
        """
        from ai_engine.models import Workflow
        from django.http import Http404

        try:
            wf = Workflow.objects.get(id=workflow_id, is_active=True)
        except Workflow.DoesNotExist:
            return json.dumps({"error": f"Workflow {workflow_id} not found or inactive"})

        return json.dumps({
            "id": wf.id,
            "name": wf.name,
            "description": wf.description or "",
            "definition": wf.definition,
        })

    # ── Tool: List recent executions ───────────────────────────────────────

    @method_tool(args_schema=ListRecentExecutionsInput)
    def list_recent_executions(self, limit: int = 5) -> str:
        """
        List the most recent workflow executions for the current user.

        Returns a JSON list of execution summaries (thread_id, status, started_at).
        """
        from ai_engine.models import WorkflowExecution, Thread

        qs = WorkflowExecution.objects.select_related("workflow", "thread")

        if self._user and self._user.is_authenticated:
            qs = qs.filter(thread__user=self._user)

        qs = qs.order_by("-started_at")[:limit]

        data = [
            {
                "execution_id": e.id,
                "thread_id": e.thread_id,
                "workflow_name": e.workflow.name,
                "status": e.status,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            }
            for e in qs
        ]
        return json.dumps({"executions": data, "count": len(data)})

    # ── Tool: Get execution status ─────────────────────────────────────────

    @method_tool
    def get_execution_status(self, thread_id: str) -> str:
        """
        Get the current status of a workflow execution by thread_id.

        Args:
            thread_id: The unique thread ID returned when the workflow was started.
        """
        from ai_engine.models import WorkflowExecution

        try:
            e = WorkflowExecution.objects.select_related("workflow").get(thread_id=thread_id)
        except WorkflowExecution.DoesNotExist:
            return json.dumps({"error": f"No execution found for thread_id: {thread_id}"})

        return json.dumps({
            "thread_id": e.thread_id,
            "workflow": e.workflow.name,
            "status": e.status,
            "input_data": e.input_data,
            "output_data": e.output_data,
            "error_message": e.error_message or None,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
        })
