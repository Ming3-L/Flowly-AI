"""
基础 LangGraph 工作流定义

一个示例工作流图：根据 LLM 输出在 chat 节点与 tool 节点之间路由。
"""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage, AIMessage  # pyright: ignore[reportMissingImports]
from langgraph.graph import END, StateGraph


# ─────────────────────────────────────────────────────────────────────────────
# State 结构（Schema）
# ─────────────────────────────────────────────────────────────────────────────

class WorkflowState(TypedDict):
    """所有工作流节点共享的 State 结构（Schema）。

    字段：
        query：原始用户问题。
        context：调用方透传的额外上下文。
        messages：完整消息历史（HumanMessage + AIMessage 链）。
        status：用于前端展示的工作流状态。
               可选值：thinking | calling_tool | finished | pending_approval | failed
        current_node：当前正在执行的节点名称。
        result：工作流完成后的最终输出。
        error：失败时的错误信息。
        resume_value：人审（human-in-the-loop）中断后恢复时由用户提供的值。
    """
    query: str
    context: dict
    messages: Annotated[list[BaseMessage], "Message history"]
    status: Annotated[str, "Current workflow status"]
    current_node: Annotated[str, "Node currently executing"]
    result: dict | None
    error: str | None
    resume_value: str | None


# ─────────────────────────────────────────────────────────────────────────────
# 节点函数（Node Functions）
# ─────────────────────────────────────────────────────────────────────────────

def chat_node(state: WorkflowState) -> WorkflowState:
    """
    LLM chat 节点：分析 query，并决定是否需要调用工具。

    LLM 返回一个结构化 JSON，包含：
        action："respond" | "call_tool" | "need_approval"
        reasoning：为何选择该 action
        tool_name：要调用的工具名（当 action == call_tool）
        tool_params：工具入参（当 action == call_tool）
        response：要展示给用户的文本回复（当 action == respond）
    """
    llm = _build_llm()

    system_prompt = (
        "You are Flowly's reasoning engine. Given the user's query, decide the next action:\n"
        '  - "respond": answer the user directly.\n'
        '  - "call_tool": call a tool (set tool_name and tool_params).\n'
        '  - "need_approval": ask the user to confirm before proceeding.\n'
        "Always respond with valid JSON."
    )

    messages = [
        ("system", system_prompt),
        ("human", state["query"]),
    ]
    # langchain 使用 (role, content) 形式的元组/对象
    ai_msg = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["query"]},
    ])

    import json
    try:
        decision = json.loads(ai_msg.content)
    except Exception:
        decision = {"action": "respond", "response": ai_msg.content}

    action = decision.get("action", "respond")
    response = decision.get("response", "")

    new_messages = state["messages"] + [ai_msg]

    if action == "respond":
        state = {
            **state,
            "messages": new_messages,
            "status": "finished",
            "current_node": "chat",
            "result": {"response": response, "reasoning": decision.get("reasoning", "")},
        }

    elif action == "call_tool":
        state = {
            **state,
            "messages": new_messages,
            "status": "calling_tool",
            "current_node": "chat",
        }
        # 将工具调用信息写入 context，供 tool 节点读取
        state["context"] = {
            **state.get("context", {}),
            "tool_name": decision.get("tool_name", "unknown"),
            "tool_params": decision.get("tool_params", {}),
        }

    elif action == "need_approval":
        state = {
            **state,
            "messages": new_messages,
            "status": "pending_approval",
            "current_node": "chat",
            "result": {
                "question": decision.get("question", "Please confirm to continue."),
                "reasoning": decision.get("reasoning", ""),
            },
        }

    return state


def tool_node(state: WorkflowState) -> WorkflowState:
    """
    工具执行节点：使用 chat 节点决策给出的参数调用工具，
    将结果追加到消息历史后，再返回给 chat 节点生成最终回复。
    """
    tool_name = state.get("context", {}).get("tool_name", "unknown")
    tool_params = state.get("context", {}).get("tool_params", {})

    # 占位工具执行器：需替换为真实的 tool 绑定
    # 例如：from langchain_core.tools import tool
    # 然后调用：result = await bound_tool.invoke(tool_params)
    result_content = f"[Tool: {tool_name}] Executed with params: {tool_params}"

    tool_msg = AIMessage(content=result_content)

    state = {
        **state,
        "messages": state["messages"] + [tool_msg],
        "status": "finished",
        "current_node": "tool",
        "result": {"tool_result": result_content},
    }

    return state


def format_response_node(state: WorkflowState) -> WorkflowState:
    """
    最终节点：将累积的消息整理为面向用户的回复，并将状态置为 finished。
    """
    last_message = state["messages"][-1] if state["messages"] else None

    response_text = (
        last_message.content if last_message else "工作流已完成，但没有输出。"
    )

    return {
        **state,
        "status": "finished",
        "current_node": "format_response",
        "result": {
            "response": response_text,
            "query": state["query"],
            "context": state.get("context", {}),
        },
    }


def approval_node(state: WorkflowState) -> WorkflowState:
    """
    人审（human-in-the-loop）节点：当工作流运行到此节点时会暂停
    （通过 LangGraph interrupt），等待用户调用 resume 接口继续执行。

    resume 接口注入的 resume_value 决定走向：
      - 通过：继续进入 format_response
      - 拒绝：跳转到失败终态
    """
    resume_value = state.get("resume_value")

    if resume_value is None:
        # 已中断：工作流 runner 理应在此调用 interrupt()
        # 这里设置一个哨兵状态，便于 API 侧提示用户
        return {
            **state,
            "status": "pending_approval",
            "current_node": "approval",
        }

    approved = resume_value.lower() in ("true", "1", "yes")
    if approved:
        return {
            **state,
            "status": "finished",
            "current_node": "approval",
            "result": {"approval": True, "message": "用户已通过。"},
        }
    else:
        return {
            **state,
            "status": "failed",
            "current_node": "approval",
            "error": "用户拒绝了待执行的操作。",
            "result": {"approval": False, "message": "用户已拒绝。"},
        }


# ─────────────────────────────────────────────────────────────────────────────
# 路由逻辑（Routing）
# ─────────────────────────────────────────────────────────────────────────────

def should_use_tool(state: WorkflowState) -> Literal["tool_node", "format_response"]:
    """chat_node 之后的路由：status=calling_tool 则走 tool_node，否则走 format_response。"""
    if state.get("status") == "calling_tool":
        return "tool_node"
    return "format_response"


def should_format_or_retry(state: WorkflowState) -> Literal["format_response", "chat_node"]:
    """tool_node 之后的路由：固定走 format_response（重试由 chat 节点处理）。"""
    return "format_response"


def should_continue_or_end(state: WorkflowState) -> Literal["format_response", "__end__"]:
    """format_response 之后的路由：固定结束。"""
    return "__end__"


# ─────────────────────────────────────────────────────────────────────────────
# 图构建（Graph Builder）
# ─────────────────────────────────────────────────────────────────────────────

def _build_llm():
    from ai_engine.workflow import get_chat_model

    return get_chat_model("openai", temperature=0.7, streaming=False)


def build_basic_workflow() -> StateGraph:
    """
    构建并编译基础工作流图。

    图结构：
        chat_node ──┬── [calling_tool] ──→ tool_node ──→ format_response ── END
                    └── [otherwise] ───────→ format_response ── END

    返回：可直接通过 .ainvoke() 调用的已编译 StateGraph。
    """
    workflow = StateGraph(WorkflowState)

    # 添加节点
    workflow.add_node("chat_node", chat_node)
    workflow.add_node("tool_node", tool_node)
    workflow.add_node("format_response", format_response_node)
    workflow.add_node("approval_node", approval_node)

    # 设置入口
    workflow.set_entry_point("chat_node")

    # 连线（Edges）
    workflow.add_conditional_edges(
        "chat_node",
        should_use_tool,
        {
            "tool_node": "tool_node",
            "format_response": "format_response",
        },
    )
    workflow.add_edge("tool_node", "format_response")
    workflow.add_edge("format_response", END)

    # 人审子路径（当 chat_node 将 status 置为 pending_approval 时触发）
    workflow.add_conditional_edges(
        "chat_node",
        lambda s: "approval_node" if s.get("status") == "pending_approval" else should_use_tool(s),
        {
            "approval_node": "approval_node",
            "tool_node": "tool_node",
            "format_response": "format_response",
        },
    )
    workflow.add_conditional_edges(
        "approval_node",
        lambda s: "__end__" if s.get("status") in ("finished", "failed") else "approval_node",
        {"__end__": END, "approval_node": "approval_node"},
    )

    return workflow


# ─────────────────────────────────────────────────────────────────────────────
# Checkpointer（Django 持久化）
# ─────────────────────────────────────────────────────────────────────────────

_checkpointer: "DjangoSaver | None" = None


def get_checkpointer() -> "DjangoSaver":
    global _checkpointer
    if _checkpointer is None:
        from langgraph.checkpoint.django.saver import DjangoSaver
        _checkpointer = DjangoSaver()
    return _checkpointer


# ─────────────────────────────────────────────────────────────────────────────
# 已编译图单例（Singleton）
# ─────────────────────────────────────────────────────────────────────────────

_compiled: StateGraph | None = None


def get_compiled_graph() -> StateGraph:
    """返回已编译的工作流图（单例）。"""
    global _compiled
    if _compiled is None:
        builder = build_basic_workflow()
        _compiled = builder.compile(checkpointer=get_checkpointer())
    return _compiled


# ─────────────────────────────────────────────────────────────────────────────
# 对外调用 API
# ─────────────────────────────────────────────────────────────────────────────

def run_workflow(
    query: str,
    context: dict | None = None,
    resume_value: str | None = None,
) -> dict:
    """
    同步入口：运行基础工作流。

    参数：
        query：用户问题。
        context：可选额外上下文。
        resume_value：当处于 pending_approval 状态时，用于恢复执行的值。

    返回：
        最终 WorkflowState 字典。
    """
    from langgraph.checkpoint.memory import MemorySaver

    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": "default"}}

    initial_input = {
        "query": query,
        "context": context or {},
        "messages": [],
        "status": "thinking",
        "current_node": "",
        "result": None,
        "error": None,
        "resume_value": resume_value,
    }

    # 当未配置 DB checkpointer 时，使用进程内 MemorySaver 运行
    try:
        result = graph.invoke(initial_input, config=config)
    except Exception:
        # 回退：DB 未就绪时使用内存 checkpointer
        mem = MemorySaver()
        builder = build_basic_workflow()
        mem_graph = builder.compile(checkpointer=mem)
        result = mem_graph.invoke(initial_input, config=config)

    return result
