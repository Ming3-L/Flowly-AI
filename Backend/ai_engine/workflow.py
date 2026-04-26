"""
LangGraph 工作流引擎——Phase 3：并行节点与高级 LangGraph 能力

核心能力（在 Phase 1 + 2 基础上扩展）：
- 异步 LLM 节点（支持结构化输出）
- 工具节点：数据库查询、HTTP 接口调用、通知等
- 人在回路：通过 interrupt() + Command(resume=True) 实现审批/确认
- 状态持久化：通过 DjangoSaver（MySQL）
- 全量流式：通过 Django Channels + WebSocket
- **Phase 3 新增**：
  * 使用 LangGraph Send API 并行 fan-out（多分支并行生成）
  * 分支逻辑：router 节点分发到不同子分支
  * 多模型支持：Claude / OpenAI / Ollama（通过工厂构建）
  * 使用 tenacity 为 LLM 与工具调用提供重试
  * 条件路由：route_to_tool 条件边
"""

from __future__ import annotations

import asyncio
import json
import os
from functools import partial
from typing import Annotated, Any, Literal, NotRequired, TypedDict

from langchain_core.language_models import BaseChatModel  # pyright: ignore[reportMissingImports]
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage  # pyright: ignore[reportMissingImports]
from langgraph.types import Send
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from tenacity import retry, stop_after_attempt, wait_exponential


# ─────────────────────────────────────────────────────────────────────────────
# State 结构定义
# ─────────────────────────────────────────────────────────────────────────────

class WorkflowState(TypedDict):
    """工作流图中各节点共享传递的状态（state）。"""

    # 核心字段
    query: str
    context: dict[str, Any]

    # 消息历史
    messages: Annotated[list[BaseMessage], add_messages]

    # 执行结果
    result: dict[str, Any] | None

    # 错误信息
    error: str | None

    # 人在回路（审批/确认）
    needs_approval: bool
    approval_question: str | None
    approval_reasoning: str | None
    approved: bool | None
    user_input: str | None

    # 工具结果
    tool_results: dict[str, Any]

    # 执行元数据
    current_node: str | None
    intent: str | None

    # ─── Phase 3 字段 ────────────────────────────────────────────────────

    # 并行执行：每个 fan-out 分支将结果写入此处。
    # key 为分支名（如 "generate_email"、"generate_report"）。
    branch_results: dict[str, Any]

    # 模型选择：本次执行使用哪个 LLM。
    # 取值示例："openai"（默认）、"claude"、"ollama"
    model_name: str

    # 路由决策：执行哪个分支。
    # 由 router 节点写入，供分支条件节点消费。
    route: str | None

    # fan-out 分支列表（router 设置，conditional Send 使用）
    branches: list[str]

    # ─── Phase 8：RAG 字段 ─────────────────────────────────────────────────
    # 当检测到知识库查询时由 rag_retrieval_node 设置。
    # 包含注入到 LLM 上下文中的检索文档片段。
    rag_context: str | None
    retrieved_documents: list[dict[str, Any]]

    # ─── 运行时注入（API / checkpointer；不会持久化到编辑器 JSON） ─
    _thread_id: NotRequired[str]
    _execution_id: NotRequired[int]
    _client_node_id: NotRequired[str]
    model_key: NotRequired[str]
    _runtime_user_id: NotRequired[int]
    _force_general_assistant: NotRequired[bool]


# 使用 TypedDict 作为完整 state 的类型标注


# ─────────────────────────────────────────────────────────────────────────────
# RAG 检索节点（Phase 8）
# ─────────────────────────────────────────────────────────────────────────────

async def rag_retrieval_node(state: WorkflowState) -> WorkflowState:
    """
    Phase 8 的 RAG 检索节点：查询工作流的向量知识库。

    触发条件：
    - router 设置 route="rag"
    - 或 query 命中知识库相关关键词（例如“在文档里”“基于上传文件”等）

    行为：
    - 检索 Top-K 相关片段，并将其作为 rag_context 注入到 state 中。
    """
    from channels.layers import get_channel_layer

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))

    await emit.node_start("rag_retrieval")

    workflow_id = state.get("context", {}).get("workflow_id")
    if not workflow_id:
        await emit.node_end("rag_retrieval", "skipped")
        return {**state, "rag_context": None, "retrieved_documents": [], "current_node": "rag_retrieval"}

    query = state.get("query", "")
    top_k = state.get("context", {}).get("rag_top_k", 5)

    try:
        from .vector_store import VectorStoreManager

        vector_store = VectorStoreManager.get_instance()
        results = vector_store.similarity_search_with_score(
            workflow_id=workflow_id,
            query=query,
            top_k=top_k,
        )

        retrieved_docs = []
        context_parts = []

        for doc, score in results:
            retrieved_docs.append({
                "content": doc.page_content,
                "score": float(score),
                "metadata": doc.metadata,
            })
            context_parts.append(
                f"[Document: {doc.metadata.get('filename', 'unknown')} | Score: {score:.4f}]\n{doc.page_content}"
            )

        rag_context = (
            "\n\n---\n\n".join(context_parts)
            if context_parts
            else ""
        )

        await emit.token(
            f"Retrieved {len(retrieved_docs)} relevant documents",
            "rag_retrieval",
        )
        await emit.node_end("rag_retrieval", "completed")

        return {
            **state,
            "rag_context": rag_context,
            "retrieved_documents": retrieved_docs,
            "current_node": "rag_retrieval",
        }

    except ImportError:
        await emit.node_end("rag_retrieval", "skipped")
        return {**state, "rag_context": None, "retrieved_documents": [], "current_node": "rag_retrieval"}
    except Exception as exc:
        await emit.workflow_error(f"RAG retrieval failed: {exc}")
        return {
            **state,
            "rag_context": None,
            "retrieved_documents": [],
            "error": str(exc),
            "current_node": "rag_retrieval",
        }


# ─────────────────────────────────────────────────────────────────────────────
# 事件推送器
# ─────────────────────────────────────────────────────────────────────────────

class WorkflowEventEmitter:
    """
    Sends structured events to the Django Channels group for the given thread.

    可选 ``execution_id``：写入 ``WorkflowExecutionStep`` 并更新 Redis 执行快照。
    """

    def __init__(self, channel_layer, thread_id: str, execution_id: int | None = None):
        self.channel_layer = channel_layer
        self.thread_id = thread_id
        self.group_name = f"workflow_{thread_id}"
        self.execution_id = execution_id

    async def _send(self, event_type: str, data: dict[str, Any]):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "workflow_event",
                "event_type": event_type,
                "data": data,
            },
        )

    async def node_start(self, node: str, **meta: Any):
        from ai_engine.workflow_execution_tracking import (
            activity_for_langgraph_node,
            persist_step_start,
            redis_set_execution_live,
        )

        title = str(meta.get("title") or meta.get("display_title") or node)
        node_kind = str(meta.get("node_type") or meta.get("node_kind") or "")
        model_route = str(meta.get("model_route") or "")
        activity = str(meta.get("activity") or "").strip() or activity_for_langgraph_node(
            node, model_route or None
        )
        payload: dict[str, Any] = {
            "node": node,
            "status": "running",
            "title": title,
            "display_title": title,
            "activity": activity,
            "node_type": node_kind,
            "model_route": model_route,
        }
        await self._send("node_start", payload)
        if self.execution_id:
            await persist_step_start(
                self.execution_id,
                node_key=node,
                display_title=title,
                node_kind=node_kind,
                activity=activity,
                model_route=model_route,
            )
            redis_set_execution_live(
                self.execution_id,
                {
                    "node": node,
                    "title": title,
                    "activity": activity,
                    "status": "running",
                    "model_route": model_route,
                    "node_type": node_kind,
                },
            )

    async def node_end(self, node: str, status: str = "completed", **meta: Any):
        from ai_engine.workflow_execution_tracking import (
            persist_step_end,
            redis_set_execution_live,
        )

        data: dict[str, Any] = {"node": node, "status": status}
        for k in ("activity", "title", "display_title", "model_route", "node_type"):
            if meta.get(k) is not None:
                data[k] = meta[k]
        await self._send("node_end", data)
        if self.execution_id:
            await persist_step_end(self.execution_id, node_key=node, end_status=status)
            redis_set_execution_live(
                self.execution_id,
                {
                    "node": node,
                    "title": str(meta.get("title") or node),
                    "activity": str(meta.get("activity") or ""),
                    "status": status,
                    "model_route": str(meta.get("model_route") or ""),
                },
            )

    async def token(self, content: str, node: str):
        await self._send("token", {"content": content, "node": node})

    async def tool_call(self, tool: str, params: dict[str, Any], node: str):
        await self._send(
            "tool_call",
            {"tool": tool, "params": params, "node": node},
        )

    async def tool_result(self, content: str, node: str):
        await self._send("tool_result", {"content": content, "node": node})

    async def workflow_end(self, status: str, result: dict[str, Any] | None = None):
        from ai_engine.workflow_execution_tracking import redis_clear_execution_live

        await self._send("workflow_end", {
            "status": status,
            "thread_id": self.thread_id,
            "result": result or {},
        })
        if self.execution_id:
            redis_clear_execution_live(self.execution_id)

    async def workflow_error(self, error: str):
        from ai_engine.workflow_execution_tracking import redis_clear_execution_live

        await self._send("workflow_error", {"error": error})
        if self.execution_id:
            redis_clear_execution_live(self.execution_id)

    async def pending_approval(self, question: str, reasoning: str, node: str):
        await self._send(
            "pending_approval",
            {"question": question, "reasoning": reasoning, "node": node},
        )

    # Phase 3：并行事件
    async def parallel_start(self, branches: list[str]):
        await self._send("parallel_start", {"branches": branches})

    async def parallel_branch_start(self, branch: str):
        await self._send("parallel_branch_start", {"branch": branch})

    async def parallel_branch_end(self, branch: str, status: str = "completed"):
        await self._send("parallel_branch_end", {"branch": branch, "status": status})

    async def parallel_end(self, status: str):
        await self._send("parallel_end", {"status": status})


# ─────────────────────────────────────────────────────────────────────────────
# 多模型工厂
# ─────────────────────────────────────────────────────────────────────────────

def get_chat_model(
    model_name: str = "openai",
    **override_kwargs,
) -> BaseChatModel:
    """
    Build a configured chat model by name.

    Supported:
      - "doubao" / "ark" : 火山方舟 OpenAI 兼容 Chat（``DOUBAO_API_KEY`` / ``ARK_API_KEY`` 等）
      - "vectorengine" : ChatOpenAI with Vector Engine API (OpenAI-compatible proxy for Codex)
      - "openai"      : ChatOpenAI（若已配置豆包密钥且未关闭 ``FLOWLY_USE_DOUBAO_DEFAULT``，则走方舟）
      - "claude"      : ChatAnthropic (uses ANTHROPIC_API_KEY)
      - "ollama"      : ChatOllama (uses OLLAMA_BASE_URL, OLLAMA_MODEL)

    Additional kwargs (e.g. temperature, streaming) override the defaults.

    密钥与端点统一来自 ``get_ai_provider_settings()``（环境变量 + project_secrets_local）。
    """
    from ai_engine.integrations import get_ai_provider_settings
    from langchain_anthropic import ChatAnthropic  # pyright: ignore[reportMissingImports]
    from langchain_ollama import ChatOllama  # pyright: ignore[reportMissingImports]
    from langchain_openai import ChatOpenAI  # pyright: ignore[reportMissingImports]

    s = get_ai_provider_settings()
    route = (model_name or "openai").strip().lower()
    if route in ("ark", "byte", "volcengine"):
        route = "doubao"
    # 仅当「未显式指定 OpenAI 模型」时，才允许把线路切到方舟默认（避免把 gpt-4o 等仍发到 Ark 导致 InvalidEndpointOrModel）
    explicit_openai_model = str(override_kwargs.get("model") or "").strip()
    if route == "openai" and s.language.doubao_ark_api_key and not explicit_openai_model:
        flag = (s.language.flowly_use_doubao_default or "1").strip().lower()
        if flag not in ("0", "false", "no", "off"):
            route = "doubao"

    if route == "doubao":
        api_key = override_kwargs.get("api_key", s.language.doubao_ark_api_key)
        if not api_key:
            raise ValueError(
                "豆包/方舟未配置：请设置环境变量 DOUBAO_API_KEY 或 ARK_API_KEY（勿提交到仓库）。"
            )
        base_url = override_kwargs.get("base_url", s.language.doubao_ark_base_url)
        raw_model = str(override_kwargs.get("model") or "").strip()
        configured = (s.language.doubao_ark_model or "").strip()
        # 显式 model（接入点 ep- 或方舟模型名如 Doubao-Smart-Router）优先于环境默认
        if raw_model:
            model_id = raw_model
        elif configured:
            model_id = configured
        else:
            raise ValueError(
                "豆包/方舟需要推理接入点：请设置 DOUBAO_ARK_MODEL（一般为 ep- 开头的 endpoint id），"
                "或在画布/预设中指定 model。"
            )
        return ChatOpenAI(
            model=model_id,
            api_key=api_key,
            base_url=base_url,
            temperature=override_kwargs.get("temperature", 0.7),
            max_tokens=override_kwargs.get("max_tokens", 1024),
            streaming=override_kwargs.get("streaming", True),
        )

    # Vector Engine（OpenAI 兼容代理，用于 Codex 等）
    if route == "vectorengine":
        return ChatOpenAI(
            model=override_kwargs.get("model", s.language.vectorengine_model or "codex"),
            api_key=override_kwargs.get("api_key", s.language.vectorengine_api_key),
            base_url=override_kwargs.get(
                "base_url",
                s.language.vectorengine_base_url or "https://api.vectorengine.cn/v1",
            ),
            temperature=override_kwargs.get("temperature", 0.7),
            streaming=override_kwargs.get("streaming", True),
        )

    if route == "claude":
        return ChatAnthropic(
            model_name=override_kwargs.get("model", s.language.anthropic_model or "claude-3-5-sonnet-20241022"),
            anthropic_api_key=override_kwargs.get("api_key", s.language.anthropic_api_key),
            temperature=override_kwargs.get("temperature", 0.7),
            max_tokens=override_kwargs.get("max_tokens", 1024),
            streaming=override_kwargs.get("streaming", True),
        )

    if route == "ollama":
        return ChatOllama(
            base_url=override_kwargs.get("base_url", s.language.ollama_base_url or "http://localhost:11434"),
            model=override_kwargs.get("model", s.language.ollama_model or "llama3"),
            temperature=override_kwargs.get("temperature", 0.7),
            streaming=override_kwargs.get("streaming", True),
        )

    # 默认：OpenAI 兼容
    return ChatOpenAI(
        model=override_kwargs.get("model", s.language.openai_model),
        api_key=override_kwargs.get("api_key", s.language.openai_api_key),
        base_url=override_kwargs.get("base_url", s.language.openai_base_url),
        temperature=override_kwargs.get("temperature", 0.7),
        streaming=override_kwargs.get("streaming", True),
    )


def get_traced_model(model: BaseChatModel, model_name: str) -> BaseChatModel:
    """如启用 tracing，则用 LangSmith @traceable 包装模型调用。"""
    import os

    tracing = os.getenv("LANGSMITH_TRACING", "").lower() in ("true", "1", "yes")
    api_key = os.getenv("LANGSMITH_API_KEY", "")
    if not (tracing and api_key):
        return model

    try:
        from langsmith import traceable

        project = os.getenv("LANGSMITH_PROJECT", "flowly-ai")
        return traceable(
            project_name=project,
            run_name=f"chat_model_{model_name}",
        )(model)
    except ImportError:
        return model


async def _async_record_llm_cost(
    state: dict[str, Any],
    response: Any,
    *,
    logical_node_name: str,
    model_fallback: str,
) -> None:
    """在线程池中写 CostRecord，避免在 async 节点里直接阻塞 Django ORM。"""
    from ai_engine.cost_tracker import record_llm_cost_for_workflow_state

    await asyncio.to_thread(
        partial(
            record_llm_cost_for_workflow_state,
            state,
            response,
            logical_node_name=logical_node_name,
            model_fallback=model_fallback,
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# 重试封装
# ─────────────────────────────────────────────────────────────────────────────

def retry_on_rate_limit_or_error(retry_state):
    """Tenacity 重试回调：遇到限流或 5xx 时返回 True 以继续重试。"""
    outcome = retry_state.outcome
    if outcome is None:
        return False
    error = str(outcome.exception() or "")
    return "rate limit" in error.lower() or "429" in error or "500" in error or "502" in error


# ─────────────────────────────────────────────────────────────────────────────
# 工具
# ─────────────────────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def query_database_tool(
    query: str,
    params: dict[str, Any] | None = None,
) -> str:
    """
    Execute a query via Django ORM and return JSON results.
    Wrapped with tenacity retry for transient DB failures.
    """
    from ai_engine.models import Workflow, WorkflowExecution, Thread

    query_lower = query.lower()

    try:
        if "workflow" in query_lower and "execution" in query_lower:
            if params and "workflow_id" in params:
                executions = WorkflowExecution.objects.filter(
                    workflow_id=params["workflow_id"]
                ).order_by("-started_at")[:10]
                results = [
                    {
                        "id": e.id,
                        "status": e.status,
                        "started_at": e.started_at.isoformat() if e.started_at else None,
                        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                    }
                    for e in executions
                ]
            else:
                results = list(Workflow.objects.all().values("id", "name", "is_active")[:20])

        elif "workflow" in query_lower:
            if params and "workflow_id" in params:
                wf = Workflow.objects.filter(id=params["workflow_id"]).first()
                if wf:
                    results = {
                        "id": wf.id,
                        "name": wf.name,
                        "description": wf.description,
                        "is_active": wf.is_active,
                        "created_at": wf.created_at.isoformat(),
                    }
                else:
                    results = {"error": f"Workflow {params['workflow_id']} not found"}
            else:
                results = list(Workflow.objects.filter(is_active=True).values(
                    "id", "name", "description", "is_active"
                ))

        elif "thread" in query_lower:
            if params and "thread_id" in params:
                thread = Thread.objects.filter(thread_id=params["thread_id"]).first()
                if thread:
                    results = {
                        "id": thread.id,
                        "thread_id": str(thread.thread_id),
                        "workflow": thread.workflow.name if thread.workflow else None,
                        "created_at": thread.created_at.isoformat(),
                    }
                else:
                    results = {"error": "Thread not found"}
            else:
                results = list(Thread.objects.all().values("id", "thread_id")[:20])

        else:
            results = list(Workflow.objects.filter(is_active=True).values(
                "id", "name", "description"
            )[:10])

        return json.dumps(results, ensure_ascii=False, indent=2)

    except Exception as exc:
        return json.dumps({"error": str(exc)})


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def call_external_api_tool(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 30,
) -> str:
    """
    Make an HTTP request to an external API.
    Retries on transient network errors and 5xx responses.
    """
    import httpx

    request_headers = {
        "User-Agent": "Flowly-AI/1.0",
        **(headers or {}),
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method=method.upper(),
                url=url,
                headers=request_headers,
                json=body,
            )
            return json.dumps({
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text[:5000],
            }, ensure_ascii=False)

    except httpx.TimeoutException:
        return json.dumps({"error": f"Request to {url} timed out after {timeout}s"})
    except httpx.RequestError as exc:
        return json.dumps({"error": f"Request failed: {exc}"})


def send_notification_tool(
    recipient: str,
    channel: str = "log",
    message: str = "",
    subject: str = "",
) -> str:
    """
    Send a notification. channel: log, email, webhook, slack.
    Retries are handled at the caller level; this function is synchronous.
    """
    from django.contrib.auth import get_user_model

    result: dict[str, Any] = {
        "recipient": recipient,
        "channel": channel,
        "subject": subject,
        "message": message,
        "delivered": False,
    }

    if channel == "log":
        result["delivered"] = True
        result["note"] = "Logged successfully"

    elif channel == "email":
        try:
            from django.core.mail import send_mail
            send_mail(
                subject=subject or "Flowly AI Notification",
                message=message,
                from_email=None,
                recipient_list=[recipient] if isinstance(recipient, str) else recipient,
                fail_silently=False,
            )
            result["delivered"] = True
        except Exception as exc:
            result["error"] = str(exc)

    elif channel == "webhook":
        webhook_result = call_external_api_tool(
            url=recipient,
            method="POST",
            headers={"Content-Type": "application/json"},
            body={"subject": subject, "message": message},
        )
        try:
            parsed = json.loads(webhook_result)
            result["delivered"] = parsed.get("status_code") == 200
            result["response"] = parsed
        except Exception:
            result["error"] = webhook_result

    elif channel == "slack":
        slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        if slack_webhook_url:
            slack_result = call_external_api_tool(
                url=slack_webhook_url,
                method="POST",
                body={"text": f"*{subject}*\n{message}"},
            )
            try:
                parsed = json.loads(slack_result)
                result["delivered"] = parsed.get("status_code") == 200
            except Exception:
                result["delivered"] = False
                result["error"] = "Slack webhook delivery failed"
        else:
            result["error"] = "SLACK_WEBHOOK_URL not configured"

    else:
        result["error"] = f"Unknown channel: {channel}"

    return json.dumps(result, ensure_ascii=False, indent=2)


def get_tools() -> list:
    """返回工作流中 LLM 可用的全部工具，并以 LangChain @tool 形式包装。"""
    from langchain_core.tools import tool  # pyright: ignore[reportMissingImports]

    @tool
    def query_database(query: str, params: str = "{}") -> str:
        """Query the database for workflows, executions, threads, or structured data.
        params should be a JSON string with optional filter keys."""
        try:
            parsed_params = json.loads(params) if params != "{}" else None
        except json.JSONDecodeError:
            parsed_params = None
        return query_database_tool(query, parsed_params)

    @tool
    def call_external_api(
        url: str,
        method: str = "GET",
        headers: str = "{}",
        body: str = "{}",
        timeout: int = 30,
    ) -> str:
        """调用外部 HTTP 接口。headers 与 body 应为 JSON 字符串。"""
        try:
            parsed_headers = json.loads(headers) if headers != "{}" else None
        except json.JSONDecodeError:
            parsed_headers = None
        try:
            parsed_body = json.loads(body) if body != "{}" else None
        except json.JSONDecodeError:
            parsed_body = None
        return call_external_api_tool(url, method, parsed_headers, parsed_body, timeout)

    @tool
    def send_notification(
        recipient: str,
        channel: str = "log",
        message: str = "",
        subject: str = "",
    ) -> str:
        """发送通知。channel：log（永远可用）、email、webhook、slack。"""
        return send_notification_tool(recipient, channel, message, subject)

    return [query_database, call_external_api, send_notification]


# ─────────────────────────────────────────────────────────────────────────────
# 系统提示词
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Flowly, an intelligent AI workflow assistant.

Your role is to help users with:
1. Querying and analyzing workflow execution data from the database
2. Making HTTP API calls to external services when needed
3. Sending notifications through various channels
4. Processing user requests and presenting clear results

**Important guidelines:**
- Always respond in the same language as the user query
- Use the `query_database` tool when users ask about workflows, executions, threads, or any data stored in the system
- Use the `call_external_api` tool to interact with external services
- Use the `send_notification` tool to deliver results or alerts
- When a user query requires approval or confirmation before proceeding (e.g. deleting data, making financial transactions, sending external notifications), you MUST ask for explicit approval
- Present results clearly with context, not just raw data
- If a tool fails, explain the error and suggest alternatives
- When the user asks for multiple types of content at once (e.g. "write me an email and a report"), respond with a JSON object listing the branches: `{"branches": ["branch_a", "branch_b"]}` so the workflow can execute them in parallel

**Workflow context:**
- You have access to the full workflow execution history
- You can look up any workflow by ID
- You can check the status of any execution
- You can retrieve all threads for a workflow

Always be helpful, precise, and proactive."""


# ─────────────────────────────────────────────────────────────────────────────
# 辅助函数：调用单个工具并推送事件
# ─────────────────────────────────────────────────────────────────────────────

async def _run_tool(
    tool_name: str,
    tool_args: dict[str, Any],
    tools: list,
    emit: WorkflowEventEmitter,
    node: str,
) -> str:
    """执行一次工具调用，推送事件，并返回结果字符串。"""
    await emit.tool_call(tool_name, tool_args, node)

    import asyncio

    try:
        tool_func = next((t for t in tools if t.name == tool_name), None)
        if tool_func:
            try:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None, lambda: tool_func.invoke(tool_args)
                )
            except Exception:
                # 回退：直接调用工具
                result = _call_tool_direct(tool_name, tool_args)
        else:
            result = f"Tool '{tool_name}' not found"
    except Exception as exc:
        result = f"Tool execution failed: {exc}"

    result_str = result if isinstance(result, str) else str(result)
    await emit.tool_result(result_str, node)
    return result_str


def _call_tool_direct(tool_name: str, args: dict[str, Any]) -> str:
    """不通过 LangChain invoke() 包装的直接工具调用。"""
    if tool_name == "query_database":
        return query_database_tool(args.get("query", ""), args.get("params"))
    elif tool_name == "call_external_api":
        return call_external_api_tool(
            args.get("url", ""),
            args.get("method", "GET"),
            args.get("headers"),
            args.get("body"),
            args.get("timeout", 30),
        )
    elif tool_name == "send_notification":
        return send_notification_tool(
            args.get("recipient", ""),
            args.get("channel", "log"),
            args.get("message", ""),
            args.get("subject", ""),
        )
    return f"Unknown tool: {tool_name}"


# ─────────────────────────────────────────────────────────────────────────────
# 节点
# ─────────────────────────────────────────────────────────────────────────────

async def router_node(state: WorkflowState) -> WorkflowState:
    """
    Phase 3 router: analyzes the query and decides the execution path.

    Classifies the query into one of:
      - "single"        : one tool call needed — go to tool_executor
      - "parallel"     : multiple independent tasks — fan out via Send API
      - "approval"     : needs human approval before proceeding
      - "general"      : general LLM assistance without tools
      - "multi_step"   : sequential multi-tool workflow

    Also selects the LLM model based on query complexity.
    """
    from channels.layers import get_channel_layer

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))

    router_model = (state.get("model_name") or "doubao").strip()
    await emit.node_start("router", model_route=router_model)

    if state.get("_force_general_assistant"):
        await emit.node_end("router")
        return {
            **state,
            "route": "general",
            "branches": [],
            "intent": "general_assistant",
            "needs_approval": False,
            "approval_question": None,
            "approval_reasoning": "",
            "model_name": router_model,
            "current_node": "router",
        }

    try:
        llm = get_chat_model(router_model)
        llm = get_traced_model(llm, router_model)

        analysis_prompt = f"""Analyze this user query and return a JSON decision:

Query: {state['query']}
Context: {json.dumps(state.get('context', {}), ensure_ascii=False)}

Respond ONLY with a JSON object:
{{
  "intent": "query_workflow" | "query_execution" | "create_workflow" | "general_assistant" | "multi_step",
  "route": "single" | "parallel" | "approval" | "general" | "multi_step",
  "branches": ["list of branch names for parallel execution — null/[] if not parallel"],
  "requires_approval": true | false,
  "approval_question": "question string if requires_approval is true, else null",
  "reasoning": "brief reasoning",
  "model_name": "openai" | "doubao" | "claude" | "ollama",
  "confidence": 0.0-1.0
}}

Examples of parallel queries:
- "send emails to alice and bob" → branches: ["send_email_alice", "send_email_bob"]
- "write me a report and an email" → branches: ["generate_report", "generate_email"]
- "search the web and query the database" → branches: ["web_search", "db_query"]

Respond ONLY with valid JSON, no additional text."""

        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=analysis_prompt),
        ])
        mf = getattr(llm, "model_name", None) or "gpt-4o"
        await _async_record_llm_cost(
            dict(state),
            response,
            logical_node_name="router",
            model_fallback=str(mf),
        )

        try:
            decision = json.loads(response.content)
        except (json.JSONDecodeError, AttributeError):
            decision = {
                "route": "general",
                "intent": "general_assistant",
                "branches": [],
                "requires_approval": False,
                "approval_question": None,
                "reasoning": response.content if hasattr(response, "content") else str(response),
                "model_name": "doubao",
                "confidence": 0.5,
            }

        route = decision.get("route", "general")
        branches = decision.get("branches") or []
        intent = decision.get("intent", "general_assistant")
        requires_approval = decision.get("requires_approval", False)
        approval_question = decision.get("approval_question")
        reasoning = decision.get("reasoning", "")
        model_name = decision.get("model_name", "doubao")

        await emit.token(reasoning, "router")
        await emit.node_end("router")

        return {
            **state,
            "route": route,
            "branches": branches,
            "intent": intent,
            "needs_approval": requires_approval,
            "approval_question": approval_question,
            "approval_reasoning": reasoning,
            "model_name": model_name,
            "current_node": "router",
        }

    except Exception as exc:
        await emit.workflow_error(f"Router failed: {exc}")
        return {
            **state,
            "route": "general",
            "branches": [],
            "error": str(exc),
            "current_node": "router",
        }


async def approval_gate(state: WorkflowState) -> WorkflowState:
    """
    Human-in-the-loop gate: pauses workflow and waits for user approval.

    The interrupt() call suspends the LangGraph state machine.
    Resume happens via the /resume API endpoint with Command(resume={...}).
    """
    from channels.layers import get_channel_layer
    from langgraph.types import interrupt

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))

    await emit.node_start("approval_gate")

    if not state.get("needs_approval", False):
        await emit.node_end("approval_gate", status="skipped")
        return {**state, "current_node": "approval_gate"}

    question = state.get("approval_question", "Do you want to proceed?")
    reasoning = state.get("approval_reasoning", "")

    await emit.pending_approval(question, reasoning, "approval_gate")

    interrupt_value = interrupt({
        "question": question,
        "reasoning": reasoning,
        "user_input": state.get("user_input", ""),
    })

    if isinstance(interrupt_value, dict):
        approved = interrupt_value.get("approved", False)
        user_input = interrupt_value.get("user_input", "")
    else:
        approved = bool(interrupt_value)
        user_input = ""

    await emit.node_end("approval_gate", status="completed" if approved else "rejected")

    return {
        **state,
        "approved": approved,
        "user_input": user_input,
        "needs_approval": False,
        "current_node": "approval_gate",
    }


# ─── Parallel branch functions ────────────────────────────────────────────────
# 这些节点函数由 Send API 调用。它们接收一份“部分 state”
#（fan_out_state 中定义的 key），并返回部分 state 的增量更新。


async def _parallel_branch_wrapper(branch: str, state: dict) -> dict:
    """
    Generic async wrapper that dispatches to the correct branch handler.

    Each handler performs its specific task and returns partial state.
    The wrapper manages channel layer, emitter, model selection, and tool execution.
    """
    from channels.layers import get_channel_layer
    from tenacity import retry, stop_after_attempt, wait_exponential

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))

    model_name = state.get("model_name", "doubao")

    # 构建带重试的模型
    def _build_and_call():
        llm = get_chat_model(model_name)
        llm = get_traced_model(llm, model_name)
        tools = get_tools()
        return llm, tools

    import asyncio

    try:
        loop = asyncio.get_running_loop()
        llm, tools = await loop.run_in_executor(None, _build_and_call)
    except Exception:
        # 同步上下文回退
        llm = get_chat_model(model_name)
        llm = get_traced_model(llm, model_name)
        tools = get_tools()

    llm_with_tools = llm.bind_tools(tools, tool_choice="auto")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    async def _invoke_llm(msgs):
        return await llm_with_tools.ainvoke(msgs)

    result_content = ""
    tool_results: dict[str, Any] = {}

    try:
        system_msg = SystemMessage(content=SYSTEM_PROMPT)
        # 将分支上下文注入到用户提示中
        user_content = f"""You are executing the branch: "{branch}"

Original query: {state['query']}

Perform the specific task for this branch and return your response.
Focus ONLY on this branch's task."""
        user_msg = HumanMessage(content=user_content)
        messages = [system_msg, user_msg]

        # 每个分支最多允许 2 次工具调用迭代
        for _ in range(2):
            response = await _invoke_llm(messages)
            if hasattr(response, "content") and response.content:
                result_content = response.content
            messages.append(response)
            mf = getattr(llm, "model_name", None) or "gpt-4o"
            await _async_record_llm_cost(
                state,
                response,
                logical_node_name=f"parallel:{branch}",
                model_fallback=str(mf),
            )

            tool_calls = getattr(response, "tool_calls", []) or []
            if not tool_calls:
                break

            for call in tool_calls:
                tool_name = call["name"]
                tool_args = call.get("args", {})
                result_str = await _run_tool(tool_name, tool_args, tools, emit, branch)
                tool_results[tool_name] = result_str
                messages.append(HumanMessage(content=f"Tool result: {result_str}"))

    except Exception as exc:
        result_content = f"[{branch}] Error: {exc}"

    return {
        "branch": branch,
        "content": result_content,
        "tool_results": tool_results,
        "error": None,
    }


async def send_email_alice_branch(state: dict) -> dict:
    """分支：向 Alice 发送邮件。"""
    from channels.layers import get_channel_layer

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))
    await emit.parallel_branch_start("send_email_alice")

    model_name = state.get("model_name", "doubao")
    llm = get_chat_model(model_name)
    llm = get_traced_model(llm, model_name)

    try:
        content = f"""Write a professional email draft for the following request:
{state['query']}

Recipient: Alice
Context: {json.dumps(state.get('context', {}), ensure_ascii=False)}

Write only the email body (professional tone)."""
        response = await llm.ainvoke([
            SystemMessage(content="You are a professional email writer."),
            HumanMessage(content=content),
        ])
        email_body = response.content if hasattr(response, "content") else str(response)
        mf = getattr(llm, "model_name", None) or "gpt-4o"
        await _async_record_llm_cost(
            state,
            response,
            logical_node_name="parallel:send_email_alice",
            model_fallback=str(mf),
        )
    except Exception as exc:
        email_body = f"[Error drafting email for Alice: {exc}]"

    await emit.parallel_branch_end("send_email_alice", "completed")
    return {
        "branch": "send_email_alice",
        "content": email_body,
        "tool_results": {},
        "error": None,
    }


async def send_email_bob_branch(state: dict) -> dict:
    """分支：向 Bob 发送邮件。"""
    from channels.layers import get_channel_layer

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))
    await emit.parallel_branch_start("send_email_bob")

    model_name = state.get("model_name", "doubao")
    llm = get_chat_model(model_name)
    llm = get_traced_model(llm, model_name)

    try:
        content = f"""Write a professional email draft for the following request:
{state['query']}

Recipient: Bob
Context: {json.dumps(state.get('context', {}), ensure_ascii=False)}

Write only the email body (professional tone)."""
        response = await llm.ainvoke([
            SystemMessage(content="You are a professional email writer."),
            HumanMessage(content=content),
        ])
        email_body = response.content if hasattr(response, "content") else str(response)
        mf = getattr(llm, "model_name", None) or "gpt-4o"
        await _async_record_llm_cost(
            state,
            response,
            logical_node_name="parallel:send_email_bob",
            model_fallback=str(mf),
        )
    except Exception as exc:
        email_body = f"[Error drafting email for Bob: {exc}]"

    await emit.parallel_branch_end("send_email_bob", "completed")
    return {
        "branch": "send_email_bob",
        "content": email_body,
        "tool_results": {},
        "error": None,
    }


async def generate_report_branch(state: dict) -> dict:
    """分支：生成报告。"""
    from channels.layers import get_channel_layer

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))
    await emit.parallel_branch_start("generate_report")

    model_name = state.get("model_name", "claude")  # 长文优先用 Claude
    llm = get_chat_model(model_name)
    llm = get_traced_model(llm, model_name)
    tools = get_tools()

    try:
        content = f"""Generate a detailed report based on the following request:
{state['query']}

Context: {json.dumps(state.get('context', {}), ensure_ascii=False)}

Include sections, data analysis where applicable, and clear conclusions."""
        response = await llm.ainvoke([
            SystemMessage(content="You are an expert data analyst and report writer."),
            HumanMessage(content=content),
        ])
        report = response.content if hasattr(response, "content") else str(response)
        mf = getattr(llm, "model_name", None) or "gpt-4o"
        await _async_record_llm_cost(
            state,
            response,
            logical_node_name="parallel:generate_report",
            model_fallback=str(mf),
        )
    except Exception as exc:
        report = f"[Error generating report: {exc}]"

    await emit.parallel_branch_end("generate_report", "completed")
    return {
        "branch": "generate_report",
        "content": report,
        "tool_results": {},
        "error": None,
    }


async def generate_email_branch(state: dict) -> dict:
    """分支：生成邮件内容。"""
    from channels.layers import get_channel_layer

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))
    await emit.parallel_branch_start("generate_email")

    model_name = state.get("model_name", "doubao")
    llm = get_chat_model(model_name)
    llm = get_traced_model(llm, model_name)

    try:
        content = f"""Write a professional email based on this request:
{state['query']}

Context: {json.dumps(state.get('context', {}), ensure_ascii=False)}

Write the email body in a clear, professional tone."""
        response = await llm.ainvoke([
            SystemMessage(content="You are a professional business writer."),
            HumanMessage(content=content),
        ])
        email_body = response.content if hasattr(response, "content") else str(response)
        mf = getattr(llm, "model_name", None) or "gpt-4o"
        await _async_record_llm_cost(
            state,
            response,
            logical_node_name="parallel:generate_email",
            model_fallback=str(mf),
        )
    except Exception as exc:
        email_body = f"[Error generating email: {exc}]"

    await emit.parallel_branch_end("generate_email", "completed")
    return {
        "branch": "generate_email",
        "content": email_body,
        "tool_results": {},
        "error": None,
    }


async def web_search_branch(state: dict) -> dict:
    """分支：执行网页搜索。"""
    from channels.layers import get_channel_layer

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))
    await emit.parallel_branch_start("web_search")

    tools = get_tools()
    tool_func = next((t for t in tools if t.name == "call_external_api"), None)

    search_result = ""
    if tool_func:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: tool_func.invoke({
                    "url": f"https://www.google.com/search?q={state['query'][:100]}",
                    "method": "GET",
                    "headers": "{}",
                    "body": "{}",
                    "timeout": 10,
                }),
            )
            search_result = result if isinstance(result, str) else str(result)
        except Exception as exc:
            search_result = f"[Web search failed: {exc}]"
    else:
        search_result = "[call_external_api tool not available]"

    await emit.parallel_branch_end("web_search", "completed")
    return {
        "branch": "web_search",
        "content": search_result,
        "tool_results": {"web_search": search_result},
        "error": None,
    }


async def db_query_branch(state: dict) -> dict:
    """分支：查询数据库。"""
    from channels.layers import get_channel_layer

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))
    await emit.parallel_branch_start("db_query")

    try:
        result = query_database_tool(state["query"])
    except Exception as exc:
        result = f"[DB query failed: {exc}]"

    await emit.parallel_branch_end("db_query", "completed")
    return {
        "branch": "db_query",
        "content": result,
        "tool_results": {"query_database": result},
        "error": None,
    }


# 分支名 → 处理函数映射
BRANCH_HANDLERS: dict[str, Any] = {
    "send_email_alice": send_email_alice_branch,
    "send_email_bob": send_email_bob_branch,
    "generate_report": generate_report_branch,
    "generate_email": generate_email_branch,
    "web_search": web_search_branch,
    "db_query": db_query_branch,
}


def _default_parallel_branch(branch: str):
    """工厂：为任意命名分支创建通用处理器。"""
    async def handler(state: dict) -> dict:
        from channels.layers import get_channel_layer

        thread_id = str(state.get("_thread_id", "unknown"))
        channel_layer = get_channel_layer()
        emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))
        await emit.parallel_branch_start(branch)

        model_name = state.get("model_name", "doubao")
        llm = get_chat_model(model_name)
        llm = get_traced_model(llm, model_name)
        tools = get_tools()
        llm_with_tools = llm.bind_tools(tools, tool_choice="auto")

        content = f"""Execute the following task for branch "{branch}":
{state['query']}

Context: {json.dumps(state.get('context', {}), ensure_ascii=False)}

Return a clear, well-structured response for this task."""
        try:
            response = await llm_with_tools.ainvoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=content),
            ])
            result = response.content if hasattr(response, "content") else str(response)
            mf = getattr(llm, "model_name", None) or "gpt-4o"
            await _async_record_llm_cost(
                state,
                response,
                logical_node_name=f"parallel:{branch}",
                model_fallback=str(mf),
            )
        except Exception as exc:
            result = f"[Branch '{branch}' failed: {exc}]"

        await emit.parallel_branch_end(branch, "completed")
        return {
            "branch": branch,
            "content": result,
            "tool_results": {},
            "error": None,
        }
    return handler


# ─── Parallel node (uses Send API) ──────────────────────────────────────────

async def parallel_executor(state: WorkflowState) -> list[dict]:
    """
    Fan-out node: uses LangGraph Send API to launch multiple branches in parallel.

    Receives state["branches"] list from router, dispatches each branch
    concurrently, collects results.

    Returns a list of partial state dicts (one per branch) that LangGraph
    will merge into WorkflowState via the special "branch_results" key.
    """
    from channels.layers import get_channel_layer

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))

    await emit.node_start("parallel_executor")
    branches = state.get("branches", [])

    if not branches:
        await emit.node_end("parallel_executor", "skipped")
        return []

    await emit.parallel_start(branches)

    # 为每个分支构建共享 state 快照
    shared_keys = ["_thread_id", "_execution_id", "_client_node_id", "query", "context", "model_name"]
    shared_state = {k: state[k] for k in shared_keys if k in state}

    # 使用 Send 并发启动所有分支
    # 实际并发由图的 Send API 执行与调度
    send_tasks = []
    for branch_name in branches:
        handler = BRANCH_HANDLERS.get(branch_name) or _default_parallel_branch(branch_name)
        # 使用 Send 扇出：每个分支使用共享 state 运行各自处理器
        send_tasks.append(
            Send(
                branch_name,
                {**shared_state, "_branch_name": branch_name},
            )
        )

    await emit.node_end("parallel_executor", "completed")
    await emit.parallel_end("all_branches_launched")

    return send_tasks


# ─── Consolidate node ───────────────────────────────────────────────────────

async def consolidate_node(state: WorkflowState) -> WorkflowState:
    """
    After parallel branches complete, consolidate their results into a unified response.

    Reads branch_results (populated by Send API), formats a combined output,
    and stores it in the result field.
    """
    from channels.layers import get_channel_layer

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))

    await emit.node_start("consolidate")

    branch_results = state.get("branch_results", {})

    if not branch_results:
        await emit.node_end("consolidate", "skipped")
        return {**state, "current_node": "consolidate"}

    # 格式化每个分支的结果
    formatted_parts = []
    for branch_name, branch_data in branch_results.items():
        content = branch_data.get("content", "")
        tool_results = branch_data.get("tool_results", {})
        formatted_parts.append(f"## [{branch_name}]\n\n{content}")

        for tool_name, tool_result in tool_results.items():
            formatted_parts.append(f"\n*Tool `{tool_name}` result:*\n{tool_result}")

    combined = "\n\n".join(formatted_parts)

    await emit.node_end("consolidate", "completed")
    await emit.workflow_end("completed", {"response": combined, "branches": list(branch_results.keys())})

    return {
        **state,
        "current_node": "consolidate",
        "result": {
            "response": combined,
            "branches": list(branch_results.keys()),
            "intent": state.get("intent"),
        },
    }


# ─── Single tool executor (existing Phase 1/2 node, now uses model_name) ──────

async def tool_executor(state: WorkflowState) -> WorkflowState:
    """
    Single-path executor: runs LLM with tools for non-parallel queries.
    Supports multi-model selection via state["model_name"].
    """
    from channels.layers import get_channel_layer

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))

    await emit.node_start("tool_executor")

    try:
        model_name = state.get("model_name", "doubao")
        llm = get_chat_model(model_name)
        llm = get_traced_model(llm, model_name)
        tools = get_tools()
        llm_with_tools = llm.bind_tools(tools, tool_choice="auto")

        system_msg = SystemMessage(content=SYSTEM_PROMPT)
        # Phase 8：如已检索到文档，则注入 RAG 上下文
        rag_context = state.get("rag_context")
        if rag_context:
            rag_system = SystemMessage(
                content=SYSTEM_PROMPT
                + f"\n\n[KNOWLEDGE BASE CONTEXT]\nThe user is asking about information in the uploaded documents. "
                  f"Use the following retrieved document chunks to answer their question. "
                  f"Cite specific information from the documents where relevant.\n\n{rag_context}\n\n[/KNOWLEDGE BASE CONTEXT]"
            )
            user_msg = HumanMessage(
                content=f"Query: {state['query']}\n\nContext: {json.dumps(state.get('context', {}), ensure_ascii=False)}"
            )
            messages = [rag_system, user_msg]
        else:
            user_msg = HumanMessage(
                content=f"Query: {state['query']}\n\nContext: {json.dumps(state.get('context', {}), ensure_ascii=False)}"
            )
            messages = [system_msg, user_msg]
        tool_results: dict[str, Any] = {}
        iteration = 0
        max_iterations = 3

        while iteration < max_iterations:
            iteration += 1
            response = await llm_with_tools.ainvoke(messages)

            if hasattr(response, "content") and response.content:
                await emit.token(response.content, "tool_executor")

            messages.append(response)
            mf = getattr(llm, "model_name", None) or "gpt-4o"
            await _async_record_llm_cost(
                dict(state),
                response,
                logical_node_name="tool_executor",
                model_fallback=str(mf),
            )
            tool_calls = getattr(response, "tool_calls", []) or []

            if not tool_calls:
                break

            for call in tool_calls:
                tool_name = call["name"]
                tool_args = call.get("args", {})
                result_str = await _run_tool(tool_name, tool_args, tools, emit, "tool_executor")
                tool_results[tool_name] = result_str

        await emit.node_end("tool_executor", "completed")

        final_content = ""
        if messages and hasattr(messages[-1], "content"):
            final_content = messages[-1].content

        return {
            **state,
            "messages": messages,
            "tool_results": tool_results,
            "current_node": "tool_executor",
            "result": {
                "response": final_content,
                "intent": state.get("intent"),
                "tools_used": list(tool_results.keys()),
                "iteration_count": iteration,
            },
        }

    except Exception as exc:
        await emit.workflow_error(f"Tool executor failed: {exc}")
        return {**state, "error": str(exc), "current_node": "tool_executor"}


# ─── General assistant (no tools) ───────────────────────────────────────────

async def general_assistant(state: WorkflowState) -> WorkflowState:
    """
    General-purpose LLM assistant without tool calls.
    Used when route="general".
    """
    from channels.layers import get_channel_layer

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))

    await emit.node_start("general_assistant")

    try:
        from ai_engine.ai_model_catalog import get_user_preset_llm_overrides, resolve_route_and_model_id

        ctx = state.get("context") or {}
        mk = str(state.get("model_key") or "").strip()
        uid = state.get("_runtime_user_id")
        if uid is not None and not isinstance(uid, int):
            try:
                uid = int(uid)
            except (TypeError, ValueError):
                uid = None

        if mk:
            # resolve_route_and_model_id / get_user_preset_llm_overrides 使用 Django ORM（仅同步）
            route, model_id, cat_key = await asyncio.to_thread(
                resolve_route_and_model_id,
                {"modelKey": mk},
                user_id=uid,
            )
            overrides = await asyncio.to_thread(get_user_preset_llm_overrides, cat_key, uid)
            llm = get_chat_model(route, model=model_id, **overrides)
            trace_route = route
            import logging
            logging.getLogger(__name__).info(
                "chat model resolved model_key=%s route=%s model_id=%s catalog_key=%s",
                mk,
                route,
                model_id,
                cat_key,
            )
        else:
            model_name = state.get("model_name", "doubao")
            llm = get_chat_model(model_name)
            trace_route = str(model_name)

        llm = get_traced_model(llm, trace_route)

        summary = str(ctx.get("_chat_rolling_summary") or "").strip()
        prior = str(ctx.get("_chat_prior_transcript") or "").strip()
        q = (state.get("query") or "").strip()
        human_parts: list[str] = []
        if summary:
            human_parts.append("【对话要点摘要】\n" + summary)
        if prior:
            human_parts.append("【近期对话摘录】\n" + prior)
        human_parts.append("【当前用户问题】\n" + q)
        human_block = "\n\n".join(human_parts)

        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_block),
        ])

        content = response.content if hasattr(response, "content") else str(response)
        mf = getattr(llm, "model_name", None) or "gpt-4o"
        await _async_record_llm_cost(
            dict(state),
            response,
            logical_node_name="general_assistant",
            model_fallback=str(mf),
        )
        await emit.token(content, "general_assistant")
        await emit.node_end("general_assistant", "completed")

        return {
            **state,
            "messages": [response],
            "current_node": "general_assistant",
            "result": {"response": content, "intent": "general_assistant"},
        }

    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception("general_assistant failed")
        await emit.workflow_error(f"General assistant failed: {exc}")
        # 避免前端“无回复”：把错误也作为 result.response 返回（同时便于落库排查）
        return {
            **state,
            "error": str(exc),
            "current_node": "general_assistant",
            "result": {"response": f"错误: {exc}", "intent": "general_assistant"},
        }


# ─── Finalize ────────────────────────────────────────────────────────────────

async def finalize_node(state: WorkflowState) -> WorkflowState:
    """
    Finalize: persist result to DB and emit workflow_end.
    """
    from channels.layers import get_channel_layer

    thread_id = str(state.get("_thread_id", "unknown"))
    channel_layer = get_channel_layer()
    emit = WorkflowEventEmitter(channel_layer, thread_id, execution_id=state.get("_execution_id"))

    await emit.node_start("finalize")

    execution_id = state.get("_execution_id")
    if execution_id:
        from asgiref.sync import sync_to_async
        from .models import WorkflowExecution
        from django.utils import timezone

        try:
            @sync_to_async(thread_sensitive=True)
            def _sync_save() -> None:
                execution = WorkflowExecution.objects.get(id=execution_id)
                execution.status = "completed"
                execution.output_data = {
                    "response": state.get("result", {}),
                    "intent": state.get("intent"),
                    "tool_results": state.get("tool_results", {}),
                    "branch_results": state.get("branch_results", {}),
                    "error": state.get("error"),
                }
                execution.completed_at = timezone.now()
                execution.save(update_fields=["status", "output_data", "completed_at"])

            await _sync_save()
        except Exception:
            pass

    await emit.node_end("finalize", "completed")
    await emit.workflow_end("completed", state.get("result"))

    return {**state, "current_node": "finalize"}


# ─────────────────────────────────────────────────────────────────────────────
# 条件边
# ─────────────────────────────────────────────────────────────────────────────

def route_decision(state: WorkflowState) -> Literal[
    "approval_gate", "rag_retrieval", "parallel_executor", "tool_executor", "general_assistant", "__end__"
]:
    """
    Phase 3 routing: after router_node, decide the next node.

    route values:
      - "approval"  → approval_gate
      - "rag"       → rag_retrieval  （Phase 8：RAG 知识库查询）
      - "parallel"  → parallel_executor  (Send API fan-out)
      - "single"    → tool_executor       (single LLM + tools)
      - "general"   → general_assistant  (no tools)
      - "multi_step"→ tool_executor       (sequential multi-tool)
      - None/error  → END
    """
    route = state.get("route")

    if route == "approval":
        return "approval_gate"
    if route == "rag":
        return "rag_retrieval"
    if route == "parallel":
        return "parallel_executor"
    if route in ("single", "multi_step"):
        return "tool_executor"
    if route == "general":
        return "general_assistant"
    return END


def after_approval(state: WorkflowState) -> Literal["parallel_executor", "tool_executor", "general_assistant", END]:
    """经过 approval_gate 后：继续到对应执行器；若拒绝则 END。"""
    if not state.get("approved", True):
        return END

    route = state.get("route", "single")
    if route == "parallel":
        return "parallel_executor"
    if route in ("single", "multi_step"):
        return "tool_executor"
    return "general_assistant"


def after_parallel(state: WorkflowState) -> Literal["consolidate"]:
    """parallel_executor 返回 list[Send] 后，LangGraph 会自动处理 fan-out。"""
    return "consolidate"


def after_rag_retrieval(state: WorkflowState) -> Literal["tool_executor", "general_assistant", END]:
    """
    After rag_retrieval: decide whether to use tools or general assistant.
    If documents were retrieved, use tool_executor (LLM can cite them).
    If no documents found, fall back to general_assistant.
    """
    retrieved = state.get("retrieved_documents", [])
    if not retrieved:
        return "general_assistant"
    return "tool_executor"


def after_consolidate(state: WorkflowState) -> Literal["finalize"]:
    """consolidate 总是流向 finalize。"""
    return "finalize"


def after_tool_executor(state: WorkflowState) -> Literal["finalize"]:
    """tool_executor 总是流向 finalize。"""
    return "finalize"


def after_general_assistant(state: WorkflowState) -> Literal["finalize"]:
    """general_assistant 总是流向 finalize。"""
    return "finalize"


# ─────────────────────────────────────────────────────────────────────────────
# 图构建：Phase 3（使用 Send API 并行 fan-out）
# ─────────────────────────────────────────────────────────────────────────────

def build_workflow_graph() -> StateGraph:
    """
    Phase 3 LangGraph workflow with:

        router_node
              │
              ▼
        route_decision ─────────────────────────────────┐
              │                                          │
              ├─ "approval"  → approval_gate             │
              │                     │                    │
              │                     ▼                    │
              │              after_approval ─────────────┤
              │                    │                     │
              ├─ "parallel"  → parallel_executor ──→ [Send API fan-out]
              │                              │
              │                              ▼
              │                         consolidate
              │                              │
              ├─ "single" / "multi_step" → tool_executor ──→
              │                                      │
              └─ "general" → general_assistant ───────┤
                                                          │
                                                          ▼
                                                       finalize
                                                          │
                                                          ▼
                                                          END

    The parallel_executor node uses the Send API to launch branch nodes
    concurrently. Each branch runs independently and returns partial state.
    The graph collects all branch results and passes them to consolidate.
    """
    workflow = StateGraph(WorkflowState)

    # ── Nodes ──────────────────────────────────────────────────────────────
    workflow.add_node("router", router_node)
    workflow.add_node("approval_gate", approval_gate)
    workflow.add_node("rag_retrieval", rag_retrieval_node)  # Phase 8：RAG
    workflow.add_node("parallel_executor", parallel_executor)
    workflow.add_node("consolidate", consolidate_node)
    workflow.add_node("tool_executor", tool_executor)
    workflow.add_node("general_assistant", general_assistant)
    workflow.add_node("finalize", finalize_node)

    # 将所有已知分支处理器注册为显式节点
    for branch_name in BRANCH_HANDLERS:
        workflow.add_node(branch_name, _default_parallel_branch(branch_name))

    # ── Entry point ────────────────────────────────────────────────────────
    workflow.set_entry_point("router")

    # ── Main routing conditional ────────────────────────────────────────────
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "approval_gate": "approval_gate",
            "rag_retrieval": "rag_retrieval",
            "parallel_executor": "parallel_executor",
            "tool_executor": "tool_executor",
            "general_assistant": "general_assistant",
            END: END,
        },
    )

    # ── Post-RAG routing: decide whether to use tools or general assistant ──
    workflow.add_conditional_edges(
        "rag_retrieval",
        after_rag_retrieval,
        {
            "tool_executor": "tool_executor",
            "general_assistant": "general_assistant",
            END: END,
        },
    )

    # ── Post-approval routing ───────────────────────────────────────────────
    workflow.add_conditional_edges(
        "approval_gate",
        after_approval,
        {
            "parallel_executor": "parallel_executor",
            "tool_executor": "tool_executor",
            "general_assistant": "general_assistant",
            END: END,
        },
    )

    # ── Post-parallel routing: Send API fan-out happens here ────────────────
    # parallel_executor 返回 list[Send]：LangGraph 会自动分发到对应命名节点，
    # 等待全部完成后再继续。
    workflow.add_edge("parallel_executor", "consolidate")
    workflow.add_edge("consolidate", "finalize")

    # ── Single-path edges ───────────────────────────────────────────────────
    workflow.add_edge("tool_executor", "finalize")
    workflow.add_edge("general_assistant", "finalize")

    # ── All paths converge at finalize ─────────────────────────────────────
    workflow.add_edge("finalize", END)

    # ── Compile with a checkpointer ─────────────────────────────────────────────
    # `langgraph.checkpoint.django` is an *optional* extra in some LangGraph builds.
    # 若缺少依赖，则回退到内存 saver，保证本地开发仍可运行。
    # 生产环境应安装正确的 checkpoint extra 以实现持久化。
    try:
        from langgraph.checkpoint.django.aio import AsyncDjangoSaver  # type: ignore[import-not-found]
    except Exception:  # pragma: no cover
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            "LangGraph Django checkpointer not available (missing 'langgraph.checkpoint.django'). "
            "Falling back to in-memory checkpointer; workflow state will NOT persist across restarts. "
            "Fix by installing LangGraph with Django checkpoint extras."
        )
        from langgraph.checkpoint.memory import MemorySaver  # type: ignore[import-not-found]

        return workflow.compile(checkpointer=MemorySaver())

    # 延迟捕获当前事件循环：AsyncDjangoSaver.sync 方法需要它，
    # 它会用 run_coroutine_threadsafe 在 sync → async 之间桥接。
    # 这里用 get_event_loop()（而不是 get_running_loop()），保证即使图在非 async
    # 上下文中构建（例如 Django 启动时）也可工作。
    _saver_loop = asyncio.get_event_loop()

    class _LoopCapturingAsyncDjangoSaver(AsyncDjangoSaver):
        def __init__(self):
            # 跳过父类 __init__（其会调用 get_running_loop()）；此处注入自有 loop。
            from langgraph.checkpoint.base import BaseCheckpointSaver
            from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
            BaseCheckpointSaver.__init__(self)
            self.jsonplus_serde = JsonPlusSerializer()
            self.lock = asyncio.Lock()
            self.loop = _saver_loop

    checkpointer = _LoopCapturingAsyncDjangoSaver()

    return workflow.compile(checkpointer=checkpointer)


# ─────────────────────────────────────────────────────────────────────────────
# 单例：延迟初始化
# ─────────────────────────────────────────────────────────────────────────────

_workflow_graph: StateGraph | None = None


def get_workflow_graph() -> StateGraph:
    """获取或创建已编译工作流图的单例。"""
    global _workflow_graph
    if _workflow_graph is None:
        _workflow_graph = build_workflow_graph()
    return _workflow_graph
