"""
AI Engine API Routes

REST API endpoints for workflow operations:
- POST /api/workflows/run         — Start a workflow execution
- GET  /api/workflows/{id}/state — Get current execution state
- POST /api/workflows/{id}/resume — Resume an interrupted workflow (human-in-the-loop)
- GET  /ws/workflow/{id}/        — WebSocket stream (see consumers.py)

All real-time events are emitted via Django Channels and delivered
to the frontend through the WebSocket consumer.
"""

import asyncio
import uuid
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router, Schema  # pyright: ignore[reportMissingImports]
from pydantic import Field  # pyright: ignore[reportMissingImports]
from ninja.security import HttpBearer  # pyright: ignore[reportMissingImports]

from .auth import JWTAuth
from .models import Workflow, WorkflowExecution, Thread
from .workflow import get_workflow_graph, WorkflowEventEmitter

# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class WorkflowRunInputSchema(Schema):
    """Input for POST /api/workflows/run."""
    workflow_id: int | None = Field(
        default=None,
        description="ID of the workflow to execute. If null, runs a free-form AI chat using general_assistant.",
    )
    query: str = Field(..., description="User query or task description")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    thread_id: str = Field(
        default="",
        description="Optional existing thread UUID to resume a session",
    )
    # Phase 3: model selection and explicit parallel override
    model_name: str = Field(
        default="openai",
        description="LLM to use: 'openai', 'claude', or 'ollama'",
    )
    parallel_branches: list[str] = Field(
        default_factory=list,
        description="Explicit list of branch names to run in parallel (optional, overrides router decision)",
    )


class WorkflowRunOutputSchema(Schema):
    """Output for POST /api/workflows/run."""
    thread_id: str
    status: str
    execution_id: int | None = None


class WorkflowStateSchema(Schema):
    """Output for GET /api/workflows/{thread_id}/state."""
    thread_id: str
    status: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowResumeInputSchema(Schema):
    """Input for POST /api/workflows/{thread_id}/resume."""
    approved: bool = Field(..., description="Whether the user approved the pending action")
    resume_input: str = Field(default="", description="User input for resuming the workflow")
    context: dict[str, Any] = Field(default_factory=dict)


class WorkflowResumeOutputSchema(Schema):
    """Output for POST /api/workflows/{thread_id}/resume."""
    thread_id: str
    status: str
    resumed: bool


# ─────────────────────────────────────────────────────────────────────────────
# Async Workflow Executor
# ─────────────────────────────────────────────────────────────────────────────

async def _run_workflow_async(
    execution_id: int,
    thread_id: str,
    workflow_id: int,
    query: str,
    context: dict[str, Any],
    model_name: str = "openai",
    parallel_branches: list[str] | None = None,
) -> None:
    """
    Execute the Phase 3 workflow using real LangGraph with Send API parallel fan-out.

    Uses `get_workflow_graph().ainvoke()` with:
    - DjangoSaver checkpointer (persists state to MySQL on each node step)
    - Thread ID as the checkpointer config key (enables resume on interruption)
    - Channels group to emit events to the WebSocket consumer
    - Parallel fan-out via Send API (branches run concurrently)
    - Multi-model support (OpenAI, Claude, Ollama)
    """
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id)

    try:
        # Update execution status to running
        with transaction.atomic():
            execution = WorkflowExecution.objects.select_for_update().get(id=execution_id)
            execution.status = "running"
            execution.save(update_fields=["status"])

        # Build initial state (Phase 3: includes model_name and parallel_branches)
        initial_state = {
            "_thread_id": thread_id,
            "_execution_id": execution_id,
            "query": query,
            "context": context,
            "messages": [],
            "result": None,
            "error": None,
            "needs_approval": False,
            "approval_question": None,
            "approval_reasoning": None,
            "approved": None,
            "user_input": None,
            "tool_results": {},
            "current_node": None,
            "intent": None,
            # Phase 3 new fields
            "branch_results": {},
            "model_name": model_name,
            "route": None,
            "branches": parallel_branches or [],
        }

        # Build LangGraph config with checkpointer
        graph_config = {"configurable": {"thread_id": thread_id}}

        # Get the compiled graph
        app = get_workflow_graph()

        # Stream through each step of the graph
        async for step in app.astream(initial_state, config=graph_config, stream_mode="values"):
            current_node = step.get("current_node")
            if not current_node:
                continue

            # Emit node start on first observation of a new node
            await emit.node_start(current_node)

            # Emit tokens if there are new messages
            messages = step.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content") and last_msg.content:
                    await emit.token(last_msg.content, current_node)

            # Emit tool call events
            tool_results = step.get("tool_results", {})
            for tool_name, result in tool_results.items():
                await emit.tool_call(tool_name, {}, current_node)
                await emit.tool_result(str(result), current_node)

            # Handle pending approval (interrupt triggered)
            if step.get("needs_approval") and step.get("approval_question"):
                await emit.pending_approval(
                    step["approval_question"],
                    step.get("approval_reasoning", ""),
                    current_node,
                )
                # Update DB to reflect paused state
                with transaction.atomic():
                    exec_obj = WorkflowExecution.objects.filter(id=execution_id).first()
                    if exec_obj:
                        exec_obj.status = "pending"
                        exec_obj.save(update_fields=["status"])
                # Interrupt here — stop streaming and wait for resume
                return

            await emit.node_end(current_node)

        # All steps complete — update execution record
        with transaction.atomic():
            execution = WorkflowExecution.objects.filter(id=execution_id).first()
            if execution:
                execution.status = "completed"
                execution.completed_at = timezone.now()
                execution.output_data = initial_state.get("result", {})
                execution.save(update_fields=["status", "completed_at", "output_data"])

        await emit.workflow_end("completed", initial_state.get("result"))

    except Exception as exc:
        with transaction.atomic():
            execution = WorkflowExecution.objects.filter(id=execution_id).first()
            if execution:
                execution.status = "failed"
                execution.error_message = str(exc)
                execution.completed_at = timezone.now()
                execution.save(update_fields=["status", "error_message", "completed_at"])

        await emit.workflow_error(str(exc))


async def _resume_workflow_async(
    execution_id: int,
    thread_id: str,
    approved: bool,
    resume_input: str,
) -> None:
    """
    Resume a workflow that was interrupted at the approval gate.

    Uses LangGraph's Command(resume=True) to continue from the interrupt point.
    """
    from langgraph.types import Command  # pyright: ignore[reportMissingImports]

    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id)

    try:
        with transaction.atomic():
            execution = WorkflowExecution.objects.select_for_update().get(id=execution_id)
            execution.status = "running"
            execution.save(update_fields=["status"])

        # Build resume state using Command
        resume_command = Command(
            resume={
                "approved": approved,
                "user_input": resume_input,
            }
        )

        app = get_workflow_graph()
        graph_config = {"configurable": {"thread_id": thread_id}}

        async for step in app.astream(resume_command, config=graph_config, stream_mode="values"):
            current_node = step.get("current_node")
            if not current_node:
                continue

            await emit.node_start(current_node)

            messages = step.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content") and last_msg.content:
                    await emit.token(last_msg.content, current_node)

            tool_results = step.get("tool_results", {})
            for tool_name, result in tool_results.items():
                await emit.tool_call(tool_name, {}, current_node)
                await emit.tool_result(str(result), current_node)

            await emit.node_end(current_node)

        with transaction.atomic():
            execution = WorkflowExecution.objects.filter(id=execution_id).first()
            if execution:
                execution.status = "completed"
                execution.completed_at = timezone.now()
                execution.output_data = step.get("result", {})
                execution.save(update_fields=["status", "completed_at", "output_data"])

        await emit.workflow_end("completed", step.get("result"))

    except Exception as exc:
        with transaction.atomic():
            execution = WorkflowExecution.objects.filter(id=execution_id).first()
            if execution:
                execution.status = "failed"
                execution.error_message = str(exc)
                execution.completed_at = timezone.now()
                execution.save(update_fields=["status", "error_message", "completed_at"])

        await emit.workflow_error(str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# API Router
# ─────────────────────────────────────────────────────────────────────────────

router = Router(tags=["Workflows"], auth=JWTAuth())


@router.post("/run", response=WorkflowRunOutputSchema)
def workflow_run(
    request: HttpRequest,
    payload: WorkflowRunInputSchema,
):
    """
    POST /api/workflows/run

    Start a new workflow execution:
    1. Validates the workflow exists and is active (optional — free chat if workflow_id is null)
    2. Creates or retrieves a Thread record (linked to authenticated user)
    3. Creates a WorkflowExecution record
    4. Joins the WebSocket channel group for this thread
    5. Spawns an async task to run the Phase 3 LangGraph
       (router → [parallel_executor | tool_executor | general_assistant] → finalize)
    6. Returns immediately with thread_id so the frontend can connect WebSocket

    Phase 3 options:
    - model_name: which LLM ("openai", "claude", "ollama")
    - parallel_branches: explicit list of branch names to fan out in parallel
    """
    current_user = request.auth  # injected by JWTAuth
    if current_user is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]
        raise AuthenticationError("Authentication required")

    # Lazy import to avoid circular dependency
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Resolve workflow (null = free-form chat via general_assistant)
    workflow = None
    if payload.workflow_id is not None:
        try:
            workflow = Workflow.objects.get(id=payload.workflow_id, is_active=True)
        except Workflow.DoesNotExist:
            return WorkflowRunOutputSchema(
                thread_id="",
                status="error",
                execution_id=None,
            )

    # Create or retrieve a Thread — associate with the authenticated user
    thread_uuid = uuid.UUID(payload.thread_id) if payload.thread_id else uuid.uuid4()
    thread, _ = Thread.objects.get_or_create(
        thread_id=thread_uuid,
        defaults={"workflow": workflow, "user": current_user},
    )

    # Create execution record
    execution = WorkflowExecution.objects.create(
        workflow=workflow,
        thread=thread,
        status="pending",
        input_data={
            "query": payload.query,
            "context": payload.context,
            "model_name": payload.model_name,
            "parallel_branches": payload.parallel_branches,
        },
    )

    # Join the WebSocket channel group
    group_name = f"workflow_{thread_uuid}"
    async_to_sync(get_channel_layer().group_add)(group_name, "workflow_events")

    # Spawn async LangGraph execution task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(
        _run_workflow_async(
            execution_id=execution.id,
            thread_id=str(thread_uuid),
            workflow_id=payload.workflow_id,
            query=payload.query,
            context=payload.context,
            model_name=payload.model_name,
            parallel_branches=payload.parallel_branches,
        )
    )

    return WorkflowRunOutputSchema(
        thread_id=str(thread_uuid),
        status="pending",
        execution_id=execution.id,
    )


@router.get("/{thread_id}/state", response=WorkflowStateSchema)
def workflow_state(request: HttpRequest, thread_id: str):
    """
    GET /api/workflows/{thread_id}/state

    Returns the current state of a workflow execution.
    Reads from the checkpointer (DjangoSaver) if available,
    falling back to the execution record in the database.
    Only returns state for executions belonging to the authenticated user.
    """
    current_user = request.auth  # injected by JWTAuth
    if current_user is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]
        raise AuthenticationError("Authentication required")

    try:
        thread_uuid = uuid.UUID(thread_id)
        execution = WorkflowExecution.objects.select_related("thread", "workflow").get(
            thread__thread_id=thread_uuid
        )
    except (WorkflowExecution.DoesNotExist, ValueError):
        return WorkflowStateSchema(
            thread_id=thread_id,
            status="not_found",
            messages=[],
            metadata={},
        )

    # Try to read from checkpointer first (gives full state including pending interrupt)
    try:
        app = get_workflow_graph()
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = app.get_state(config)

        if checkpoint and checkpoint.values:
            messages = [
                {"role": getattr(m, "type", "unknown"), "content": getattr(m, "content", str(m))}
                for m in checkpoint.values.get("messages", [])
            ]
        else:
            messages = execution.input_data.get("messages", [])
    except Exception:
        messages = execution.input_data.get("messages", [])

    # Authorization: only allow access to threads owned by the current user
    if execution.thread is not None and execution.thread.user_id != current_user.id:
        return WorkflowStateSchema(
            thread_id=thread_id,
            status="forbidden",
            messages=[],
            metadata={},
        )

    return WorkflowStateSchema(
        thread_id=thread_id,
        status=execution.status,
        messages=messages,
        metadata={
            "execution_id": execution.id,
            "workflow_id": execution.workflow_id,
            "workflow_name": execution.workflow.name if execution.workflow else None,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "error": execution.error_message or None,
        },
    )


@router.post("/{thread_id}/resume", response=WorkflowResumeOutputSchema)
def workflow_resume(
    request: HttpRequest,
    thread_id: str,
    payload: WorkflowResumeInputSchema,
):
    """
    POST /api/workflows/{thread_id}/resume

    Human-in-the-loop: resume a workflow that was interrupted at an approval gate.
    Only the owner of the thread can resume it.

    When a workflow emits `pending_approval`, execution pauses. The user reviews
    the question in the frontend and calls this endpoint with their decision.
    If approved, the workflow continues from the interrupt point. If rejected,
    the workflow is marked as failed.
    """
    current_user = request.auth
    if current_user is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]
        raise AuthenticationError("Authentication required")
    try:
        execution = WorkflowExecution.objects.select_related("thread").get(
            thread__thread_id=thread_id
        )
    except WorkflowExecution.DoesNotExist:
        return WorkflowResumeOutputSchema(
            thread_id=thread_id,
            status="not_found",
            resumed=False,
        )

    # Authorization: only the thread owner can resume
    if execution.thread is not None and execution.thread.user_id != current_user.id:
        return WorkflowResumeOutputSchema(
            thread_id=thread_id,
            status="forbidden",
            resumed=False,
        )

    # Reject path — abort immediately
    if not payload.approved:
        execution.status = "failed"
        execution.error_message = f"Execution rejected by user: {payload.resume_input}"
        execution.completed_at = timezone.now()
        execution.save()

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"workflow_{thread_id}",
            {
                "type": "workflow_event",
                "event_type": "workflow_end",
                "data": {"status": "rejected", "thread_id": thread_id},
            },
        )
        return WorkflowResumeOutputSchema(
            thread_id=thread_id,
            status="failed",
            resumed=True,
        )

    # Approve path — update execution and resume async task
    execution.status = "running"
    execution.save(update_fields=["status"])

    # Notify frontend that execution is resuming
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"workflow_{thread_id}",
        {
            "type": "workflow_event",
            "event_type": "workflow_resumed",
            "data": {
                "approved": True,
                "user_input": payload.resume_input,
                "status": "running",
            },
        },
    )

    # Spawn resume task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(
        _resume_workflow_async(
            execution_id=execution.id,
            thread_id=thread_id,
            approved=True,
            resume_input=payload.resume_input,
        )
    )

    return WorkflowResumeOutputSchema(
        thread_id=thread_id,
        status="running",
        resumed=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Legacy Endpoints (backward compatibility)
# ─────────────────────────────────────────────────────────────────────────────

class LegacyWorkflowInputSchema(Schema):
    query: str = Field(..., description="User query or task description")
    context: dict[str, Any] = Field(default_factory=dict)


class LegacyWorkflowOutputSchema(Schema):
    thread_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None


legacy_router = Router(tags=["AI Engine"], auth=JWTAuth())


@legacy_router.post("/execute", response=LegacyWorkflowOutputSchema)
async def legacy_workflow_execute(
    request: HttpRequest,
    payload: LegacyWorkflowInputSchema,
):
    """
    POST /api/ai/execute (legacy)

    Creates a pending execution and starts the real LangGraph runner.
    Frontend should connect to WebSocket at /ws/workflow/<thread_id>/ for events.
    """
    current_user = request.auth
    if current_user is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]
        raise AuthenticationError("Authentication required")

    try:
        thread_uuid = uuid.uuid4()

        # Create a default workflow if none exist
        workflow, _ = Workflow.objects.get_or_create(
            name="default",
            defaults={
                "description": "Default workflow",
                "definition": {"nodes": [{"id": "chat", "type": "chat", "name": "Chat Node"}]},
            },
        )

        thread = Thread.objects.create(thread_id=thread_uuid, workflow=workflow, user=current_user)

        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            thread=thread,
            status="pending",
            input_data={"query": payload.query, "context": payload.context},
        )

        group_name = f"workflow_{thread_uuid}"
        async_to_sync(get_channel_layer().group_add)(group_name, "workflow_events")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(
            _run_workflow_async(
                execution_id=execution.id,
                thread_id=str(thread_uuid),
                workflow_id=workflow.id,
                query=payload.query,
                context=payload.context,
            )
        )

        return LegacyWorkflowOutputSchema(
            thread_id=str(thread_uuid),
            status="pending",
            result=None,
        )

    except Exception as e:
        return LegacyWorkflowOutputSchema(
            thread_id="",
            status="error",
            result=None,
            error=str(e),
        )


@legacy_router.get("/status/{thread_id}")
async def legacy_workflow_status(
    request: HttpRequest,
    thread_id: str,
):
    """GET /api/ai/status/{thread_id} (legacy)."""
    current_user = request.auth
    if current_user is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]
        raise AuthenticationError("Authentication required")
    try:
        execution = WorkflowExecution.objects.select_related("thread").get(
            thread__thread_id=thread_id
        )
    except WorkflowExecution.DoesNotExist:
        return {
            "thread_id": thread_id,
            "status": "not_found",
            "messages": [],
            "metadata": {},
        }
    # Authorization
    if execution.thread is not None and execution.thread.user_id != current_user.id:
        return {
            "thread_id": thread_id,
            "status": "forbidden",
            "messages": [],
            "metadata": {},
        }
    return {
        "thread_id": thread_id,
        "status": execution.status,
        "messages": [],
        "metadata": {},
    }
