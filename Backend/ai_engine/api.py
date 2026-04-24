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
import logging
import threading
import uuid
from typing import Any, Coroutine
import time

from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema  # pyright: ignore[reportMissingImports]
from pydantic import Field  # pyright: ignore[reportMissingImports]
from ninja.security import HttpBearer  # pyright: ignore[reportMissingImports]

from .auth import JWTAuth
from .models import Workflow, WorkflowExecution, Thread, WorkflowExecutionStep
from .workflow import get_workflow_graph, WorkflowEventEmitter
from .workflow_nodes.cost_context import clear_llm_cost_context, set_llm_cost_context
from .workflow_nodes.execution import execute_canvas_node
from .workflow_graph.canvas_runner import run_canvas_workflow_async

logger = logging.getLogger(__name__)


@sync_to_async(thread_sensitive=True)
def _sync_update_execution_status(execution_id: int, *, status: str) -> dict[str, Any]:
    with transaction.atomic():
        ex = WorkflowExecution.objects.select_for_update().filter(id=int(execution_id)).first()
        if not ex:
            return {"ok": False}
        ex.status = str(status)
        ex.save(update_fields=["status"])
        return {"ok": True}


@sync_to_async(thread_sensitive=True)
def _sync_mark_execution_pending(execution_id: int) -> None:
    with transaction.atomic():
        ex = WorkflowExecution.objects.select_for_update().filter(id=int(execution_id)).first()
        if ex:
            ex.status = "pending"
            ex.save(update_fields=["status"])


@sync_to_async(thread_sensitive=True)
def _sync_mark_execution_completed(execution_id: int, *, output: dict[str, Any]) -> dict[str, Any]:
    with transaction.atomic():
        ex = WorkflowExecution.objects.select_for_update().filter(id=int(execution_id)).first()
        if not ex:
            return {}
        inp = dict(ex.input_data or {})
        ex.status = "completed"
        ex.completed_at = timezone.now()
        ex.output_data = output
        ex.save(update_fields=["status", "completed_at", "output_data"])
        return inp


@sync_to_async(thread_sensitive=True)
def _sync_mark_execution_failed(execution_id: int, *, err: str) -> dict[str, Any]:
    with transaction.atomic():
        ex = WorkflowExecution.objects.select_for_update().filter(id=int(execution_id)).select_related("thread").first()
        if not ex:
            return {"input_data": {}, "user_id": None}
        ex.status = "failed"
        ex.error_message = str(err)
        ex.completed_at = timezone.now()
        ex.save(update_fields=["status", "error_message", "completed_at"])
        uid = ex.thread.user_id if ex.thread_id else None
        return {"input_data": dict(ex.input_data or {}), "user_id": uid}


def _spawn_background_async(coro: Coroutine[Any, Any, None]) -> None:
    """
    在守护线程中运行协程，供同步 Ninja 视图在返回 HTTP 响应后继续执行工作流。

    注意：仅用 ``loop.create_task`` 而不 ``run_until_complete`` 时，任务永远不会被调度。
    """

    def _runner() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            logger.info("bg-workflow thread started")
            loop.run_until_complete(coro)
        except Exception:
            logger.exception("Background workflow coroutine failed")
        finally:
            try:
                loop.close()
            except Exception:
                pass

    threading.Thread(target=_runner, daemon=True, name="flowly-bg-workflow").start()


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
        default="doubao",
        description="LLM 路由：'doubao'（火山方舟，默认）、'openai'、'claude'、'ollama' 等",
    )
    parallel_branches: list[str] = Field(
        default_factory=list,
        description="Explicit list of branch names to run in parallel (optional, overrides router decision)",
    )
    client_node_id: str = Field(
        default="",
        description="可选：画布节点 id，用于 CostRecord 与 token 用量对齐",
    )
    conversation_session_id: int | None = Field(
        default=None,
        description="可选：独立 AI 对话会话 id（仅当 workflow_id 为空时生效）；服务端落库多轮上下文",
    )
    model_key: str = Field(
        default="",
        description="可选：模型目录键（如 gpt-4o、user:xxx），与画布一致；空则沿用 model_name 路由",
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


class CanvasNodeRunInputSchema(Schema):
    """POST /api/workflows/canvas-node/run — 执行单个画布节点。"""

    workflow_id: int = Field(..., description="所属工作流 id")
    client_node_id: str = Field(..., min_length=1, max_length=128, description="与编辑器节点 id 一致")
    node_type: str = Field(..., min_length=1, max_length=64, description="如 chat 或 ut_<自定义类型主键>")
    config: dict[str, Any] = Field(default_factory=dict)
    inputs: dict[str, Any] = Field(default_factory=dict)


class CanvasNodeRunOutputSchema(Schema):
    execution_id: int
    status: str
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class CanvasWorkflowRunInputSchema(Schema):
    """POST /api/workflows/canvas/run — 按画布 nodes/edges 串联执行整个工作流。"""

    workflow_id: int = Field(..., description="所属工作流 id")
    thread_id: str = Field(default="", description="可选：复用 thread uuid；为空则新建")
    entry_node_id: str = Field(default="", description="可选：指定起始节点 id")
    initial_inputs: dict[str, Any] = Field(default_factory=dict, description="起始节点 inputs（可选）")
    query: str = Field(default="", description="用户主查询，将写入 initial_inputs.text / query")
    context: dict[str, Any] = Field(default_factory=dict, description="与运行页一致的上下文 JSON")


class CanvasWorkflowRunOutputSchema(Schema):
    thread_id: str
    status: str
    execution_id: int | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Async Workflow Executor
# ─────────────────────────────────────────────────────────────────────────────

async def _run_workflow_async(
    execution_id: int,
    thread_id: str,
    workflow_id: int | None,
    query: str,
    context: dict[str, Any],
    model_name: str = "doubao",
    parallel_branches: list[str] | None = None,
    client_node_id: str = "",
    *,
    force_general_assistant: bool = False,
    model_key: str = "",
    runtime_user_id: int | None = None,
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
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=execution_id)
    set_llm_cost_context(execution_id=execution_id, client_node_id=client_node_id or "")

    try:
        t0 = time.monotonic()
        logger.info(
            "workflow_async start execution_id=%s thread_id=%s workflow_id=%s model_name=%s model_key=%s runtime_user_id=%s force_general=%s",
            execution_id,
            thread_id,
            workflow_id,
            model_name,
            (model_key or ""),
            runtime_user_id,
            force_general_assistant,
        )
        # Update execution status to running (Django ORM is sync-only)
        await _sync_update_execution_status(execution_id, status="running")

        # Build initial state (Phase 3: includes model_name and parallel_branches)
        initial_state: dict[str, Any] = {
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
            "_client_node_id": client_node_id or "",
        }
        if (model_key or "").strip():
            initial_state["model_key"] = (model_key or "").strip()
        if runtime_user_id is not None:
            initial_state["_runtime_user_id"] = int(runtime_user_id)
        if force_general_assistant:
            initial_state["_force_general_assistant"] = True

        # Build LangGraph config with checkpointer
        graph_config = {"configurable": {"thread_id": thread_id}}

        # Get the compiled graph
        app = get_workflow_graph()

        last_announced: str | None = None
        last_step: dict[str, Any] | None = None

        # Stream through each step of the graph
        async for step in app.astream(initial_state, config=graph_config, stream_mode="values"):
            last_step = step
            current_node = step.get("current_node")
            if not current_node:
                continue

            mn = str(step.get("model_name") or model_name or "doubao").strip()
            if current_node != last_announced:
                if last_announced is not None:
                    await emit.node_end(last_announced)
                await emit.node_start(current_node, model_route=mn, title=current_node, node_type="langgraph")
                last_announced = current_node
                logger.info(
                    "workflow_async node_start execution_id=%s thread_id=%s node=%s model_route=%s",
                    execution_id,
                    thread_id,
                    current_node,
                    mn,
                )

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
                await _sync_mark_execution_pending(execution_id)
                if last_announced is not None:
                    await emit.node_end(last_announced)
                # Interrupt here — stop streaming and wait for resume
                return

        if last_announced is not None:
            await emit.node_end(last_announced)

        final_result: dict[str, Any] = {}
        if last_step is not None:
            fr = last_step.get("result")
            if isinstance(fr, dict):
                final_result = fr

        # All steps complete — update execution record (sync ORM)
        inp = await _sync_mark_execution_completed(execution_id, output=final_result)

        cid = inp.get("conversation_session_id")
        if isinstance(cid, int) and final_result:
            try:
                from ai_engine.conversation.persist import record_assistant_reply

                resp = ""
                if isinstance(final_result, dict):
                    resp = str(final_result.get("response") or "").strip()
                # 即使为空也落库一条，避免前端“永远无回复”
                if not resp:
                    resp = "（空响应）"
                logger.info("chat persist assistant_reply session_id=%s chars=%s", cid, len(resp))
                await sync_to_async(record_assistant_reply, thread_sensitive=True)(
                    session_id=cid,
                    content=resp,
                )
            except Exception:
                logger.exception("record_assistant_reply failed")

        await emit.workflow_end("completed", final_result)
        logger.info(
            "workflow_async end execution_id=%s thread_id=%s status=completed elapsed_s=%.3f",
            execution_id,
            thread_id,
            time.monotonic() - t0,
        )

    except Exception as exc:
        failed_ctx = await _sync_mark_execution_failed(execution_id, err=str(exc))
        raw_in = dict(failed_ctx.get("input_data") or {})
        cid = raw_in.get("conversation_session_id")
        uid = failed_ctx.get("user_id")
        if isinstance(cid, int) and uid and raw_in.get("conversation_append_user"):
            try:
                from ai_engine.conversation.persist import remove_last_message_if_role
                from ai_engine.models import ConversationMessage

                await sync_to_async(remove_last_message_if_role, thread_sensitive=True)(
                    session_id=cid,
                    user_id=int(uid),
                    role=ConversationMessage.Role.USER,
                )
            except Exception:
                logger.exception("remove_last_message_if_role failed")

        await emit.workflow_error(str(exc))
        logger.exception(
            "workflow_async end execution_id=%s thread_id=%s status=failed elapsed_s=%.3f",
            execution_id,
            thread_id,
            time.monotonic() - t0 if "t0" in locals() else -1.0,
        )
    finally:
        clear_llm_cost_context()


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
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=execution_id)

    def _resume_client_node_id() -> str:
        ex = WorkflowExecution.objects.filter(pk=execution_id).first()
        if not ex or not ex.input_data:
            return ""
        return str(ex.input_data.get("client_node_id") or "")

    cid = await asyncio.to_thread(_resume_client_node_id)
    set_llm_cost_context(execution_id=execution_id, client_node_id=cid)

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

        last_announced: str | None = None
        last_step: dict[str, Any] | None = None

        async for step in app.astream(resume_command, config=graph_config, stream_mode="values"):
            last_step = step
            current_node = step.get("current_node")
            if not current_node:
                continue

            mn = str(step.get("model_name") or "doubao").strip()
            if current_node != last_announced:
                if last_announced is not None:
                    await emit.node_end(last_announced)
                await emit.node_start(current_node, model_route=mn, title=current_node, node_type="langgraph")
                last_announced = current_node

            messages = step.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content") and last_msg.content:
                    await emit.token(last_msg.content, current_node)

            tool_results = step.get("tool_results", {})
            for tool_name, result in tool_results.items():
                await emit.tool_call(tool_name, {}, current_node)
                await emit.tool_result(str(result), current_node)

        if last_announced is not None:
            await emit.node_end(last_announced)

        final_result: dict[str, Any] = {}
        if last_step is not None:
            fr = last_step.get("result")
            if isinstance(fr, dict):
                final_result = fr

        with transaction.atomic():
            execution = WorkflowExecution.objects.filter(id=execution_id).first()
            if execution:
                execution.status = "completed"
                execution.completed_at = timezone.now()
                execution.output_data = final_result
                execution.save(update_fields=["status", "completed_at", "output_data"])

        await emit.workflow_end("completed", final_result)

    except Exception as exc:
        with transaction.atomic():
            execution = WorkflowExecution.objects.filter(id=execution_id).first()
            if execution:
                execution.status = "failed"
                execution.error_message = str(exc)
                execution.completed_at = timezone.now()
                execution.save(update_fields=["status", "error_message", "completed_at"])

        await emit.workflow_error(str(exc))
    finally:
        clear_llm_cost_context()


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
            workflow = Workflow.objects.get(
                id=payload.workflow_id,
                user=current_user,
                is_active=True,
                is_deleted=False,
            )
        except Workflow.DoesNotExist:
            return WorkflowRunOutputSchema(
                thread_id="",
                status="error",
                execution_id=None,
            )
    else:
        # Create a default "free chat" workflow if none exists
        workflow, _ = Workflow.objects.get_or_create(
            name="general_assistant",
            defaults={
                "description": "Default free-form AI chat workflow",
                "definition": {"nodes": [{"id": "chat", "type": "chat", "name": "AI Chat"}]},
            },
        )

    # Create or retrieve a Thread — associate with the authenticated user
    thread_uuid = uuid.UUID(payload.thread_id) if payload.thread_id else uuid.uuid4()
    thread, _ = Thread.objects.get_or_create(
        thread_id=thread_uuid,
        defaults={"workflow": workflow, "user": current_user},
    )
    logger.info(
        "workflows.run request user_id=%s thread_id=%s workflow_id=%s conv_session_id=%s model_name=%s model_key=%s",
        getattr(current_user, "pk", None),
        str(thread_uuid),
        payload.workflow_id,
        payload.conversation_session_id,
        payload.model_name,
        (payload.model_key or "").strip(),
    )

    conv_id = payload.conversation_session_id
    ctx = dict(payload.context or {})
    query_eff = (payload.query or "").strip()
    force_g = False
    append_conv = False
    model_key_eff = (payload.model_key or "").strip()

    if conv_id is not None and payload.workflow_id is None:
        from ai_engine.conversation import persist as chat_persist
        from ai_engine.models import ConversationSession

        try:
            sess = chat_persist.get_session_for_user(session_id=conv_id, user_id=current_user.pk)
            extra, latest_query = chat_persist.append_user_and_prepare_context(session=sess, user_text=query_eff)
            ctx.update(extra)
            query_eff = latest_query
            force_g = True
            append_conv = True
        except ConversationSession.DoesNotExist:
            return WorkflowRunOutputSchema(
                thread_id="",
                status="error",
                execution_id=None,
            )

    # Create execution record
    execution = WorkflowExecution.objects.create(
        workflow=workflow,
        thread=thread,
        status="pending",
        input_data={
            "query": query_eff,
            "context": ctx,
            "model_name": payload.model_name,
            "parallel_branches": payload.parallel_branches,
            "client_node_id": payload.client_node_id or "",
            "conversation_session_id": conv_id,
            "model_key": model_key_eff,
            "runtime_user_id_for_catalog": current_user.pk,
            "force_general_assistant": force_g,
            "conversation_append_user": append_conv,
        },
    )

    _spawn_background_async(
        _run_workflow_async(
            execution_id=execution.id,
            thread_id=str(thread_uuid),
            workflow_id=payload.workflow_id,
            query=query_eff,
            context=ctx,
            model_name=payload.model_name,
            parallel_branches=payload.parallel_branches,
            client_node_id=payload.client_node_id or "",
            force_general_assistant=force_g,
            model_key=model_key_eff,
            runtime_user_id=current_user.pk,
        )
    )
    logger.info(
        "workflows.run spawned execution_id=%s thread_id=%s status=pending",
        execution.id,
        str(thread_uuid),
    )

    return WorkflowRunOutputSchema(
        thread_id=str(thread_uuid),
        status="pending",
        execution_id=execution.id,
    )


@router.post("/canvas-node/run", response=CanvasNodeRunOutputSchema)
def run_canvas_node_endpoint(request: HttpRequest, payload: CanvasNodeRunInputSchema):
    """
    POST /api/workflows/canvas-node/run

    同步执行单个画布节点，写入 ``WorkflowExecution`` 并触发 ``CostRecord``（含 ``client_node_id``）。
    """
    current_user = request.auth
    if current_user is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")

    wf = get_object_or_404(Workflow, id=payload.workflow_id, user=current_user)
    execution = WorkflowExecution.objects.create(
        workflow=wf,
        thread=None,
        status="running",
        input_data={
            "client_node_id": payload.client_node_id,
            "node_type": payload.node_type,
            "config": payload.config,
            "inputs": payload.inputs,
        },
    )
    try:
        output = execute_canvas_node(
            node_type=payload.node_type,
            config=payload.config,
            inputs=payload.inputs,
            user_id=current_user.id,
            execution=execution,
            client_node_id=payload.client_node_id,
        )
        execution.status = "completed"
        execution.output_data = output
        execution.completed_at = timezone.now()
        execution.save(update_fields=["status", "output_data", "completed_at"])
        return CanvasNodeRunOutputSchema(
            execution_id=execution.id,
            status="completed",
            output=output,
            error=None,
        )
    except Exception as exc:
        execution.refresh_from_db()
        return CanvasNodeRunOutputSchema(
            execution_id=execution.id,
            status=execution.status,
            output=execution.output_data or {},
            error=str(exc),
        )


@router.post("/canvas/run", response=CanvasWorkflowRunOutputSchema)
def run_canvas_workflow_endpoint(request: HttpRequest, payload: CanvasWorkflowRunInputSchema):
    """
    POST /api/workflows/canvas/run

    串联执行 workflow.definition（nodes/edges）并通过 WebSocket 推送节点进度与中间输出。
    """
    current_user = request.auth
    if current_user is None:
        from ninja.errors import AuthenticationError  # pyright: ignore[reportMissingImports]

        raise AuthenticationError("Authentication required")

    wf = get_object_or_404(Workflow, id=payload.workflow_id, user=current_user)

    # Create or retrieve a Thread for WS streaming
    thread_uuid = uuid.UUID(payload.thread_id) if payload.thread_id else uuid.uuid4()
    thread, _ = Thread.objects.get_or_create(
        thread_id=thread_uuid,
        defaults={"workflow": wf, "user": current_user},
    )

    merged_inputs = dict(payload.initial_inputs or {})
    if payload.query and payload.query.strip():
        q = payload.query.strip()
        merged_inputs.setdefault("text", q)
        merged_inputs.setdefault("query", q)
    if payload.context:
        merged_inputs.setdefault("context", payload.context)

    execution = WorkflowExecution.objects.create(
        workflow=wf,
        thread=thread,
        status="pending",
        input_data={
            "workflow_id": wf.id,
            "entry_node_id": payload.entry_node_id or "",
            "initial_inputs": merged_inputs,
            "query": payload.query or "",
            "context": payload.context or {},
        },
    )

    _spawn_background_async(
        run_canvas_workflow_async(
            workflow=wf,
            execution=execution,
            thread_id=str(thread_uuid),
            user_id=current_user.id,
            entry_node_id=payload.entry_node_id or None,
            initial_inputs=merged_inputs,
        )
    )

    return CanvasWorkflowRunOutputSchema(
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
    except ValueError:
        return WorkflowStateSchema(
            thread_id=thread_id,
            status="not_found",
            messages=[],
            metadata={},
        )

    execution = (
        WorkflowExecution.objects.select_related("thread", "workflow")
        .filter(thread__thread_id=thread_uuid)
        .order_by("-id")
        .first()
    )
    if execution is None:
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

    from ai_engine.workflow_execution_tracking import redis_get_execution_live

    node_steps = []
    for row in WorkflowExecutionStep.objects.filter(execution_id=execution.id).order_by("id"):
        node_steps.append(
            {
                "node_key": row.node_key,
                "display_title": row.display_title,
                "node_kind": row.node_kind,
                "activity": row.activity,
                "model_route": row.model_route,
                "status": row.status,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            }
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
            "node_steps": node_steps,
            "execution_live": redis_get_execution_live(execution.id),
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
        thread_uuid = uuid.UUID(str(thread_id).strip())
    except ValueError:
        return WorkflowResumeOutputSchema(
            thread_id=thread_id,
            status="not_found",
            resumed=False,
        )

    execution = (
        WorkflowExecution.objects.select_related("thread")
        .filter(thread__thread_id=thread_uuid, status="pending")
        .order_by("-id")
        .first()
    )
    if execution is None:
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

    _spawn_background_async(
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

        async def _legacy_runner() -> None:
            try:
                await _run_workflow_async(
                    execution_id=execution.id,
                    thread_id=str(thread_uuid),
                    workflow_id=workflow.id,
                    query=payload.query,
                    context=payload.context,
                    client_node_id="",
                )
            except Exception:
                logger.exception("Legacy /api/ai/execute workflow failed")

        _spawn_background_async(_legacy_runner())

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
