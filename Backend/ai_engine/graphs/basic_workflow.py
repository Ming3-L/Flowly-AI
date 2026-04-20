"""
Basic LangGraph Workflow Definition

A simple workflow graph demonstrating routing between a chat node
and a tool node based on the LLM's output.
"""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage, AIMessage  # pyright: ignore[reportMissingImports]
from langchain_openai import ChatOpenAI  # pyright: ignore[reportMissingImports]
from langgraph.graph import END, StateGraph


# ─────────────────────────────────────────────────────────────────────────────
# State Schema
# ─────────────────────────────────────────────────────────────────────────────

class WorkflowState(TypedDict):
    """State schema shared across all workflow nodes.

    Fields:
        query:        Original user query.
        context:      Additional context passed by the caller.
        messages:     Full message history (HumanMessage + AIMessage chain).
        status:       Current workflow status for frontend display.
                      Values: thinking | calling_tool | finished | pending_approval | failed
        current_node: Name of the node currently executing.
        result:       Final output after workflow completes.
        error:        Error message if workflow fails.
        resume_value: User-supplied value when resuming from a human-in-the-loop interrupt.
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
# Node Functions
# ─────────────────────────────────────────────────────────────────────────────

def chat_node(state: WorkflowState) -> WorkflowState:
    """
    LLM chat node. Analyses the query and decides whether a tool must be called.

    The LLM returns a structured JSON with:
        action: "respond" | "call_tool" | "need_approval"
        reasoning: why this action was chosen
        tool_name: name of the tool to call (if action == call_tool)
        tool_params: parameters for the tool (if action == call_tool)
        response: text response to show to the user (if action == respond)
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
    # langchain uses (role, content) tuples
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
        # store tool call in context for the tool node to pick up
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
    Tool execution node. Runs a tool using the parameters provided
    by the chat node's decision, then appends the result to the message
    history and returns control to the chat node for final response.
    """
    tool_name = state.get("context", {}).get("tool_name", "unknown")
    tool_params = state.get("context", {}).get("tool_params", {})

    # Placeholder tool executor — replace with actual tool bindings
    # e.g. from langchain_core.tools import tool
    # and call: result = await bound_tool.invoke(tool_params)
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
    Final node. Formats the accumulated messages into a clean user-facing
    response and sets the workflow status to finished.
    """
    last_message = state["messages"][-1] if state["messages"] else None

    response_text = (
        last_message.content if last_message else "Workflow completed with no output."
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
    Human-in-the-loop node. When the workflow reaches this node it pauses
    (via LangGraph interrupt) waiting for the user to call the resume endpoint.

    The resume_value injected by the resume endpoint controls the flow:
      - If approved: continue to format_response.
      - If rejected: jump to the failed terminal.
    """
    resume_value = state.get("resume_value")

    if resume_value is None:
        # Interrupted — the workflow runner should have called interrupt() here.
        # We set a sentinel so the API consumer knows to prompt the user.
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
            "result": {"approval": True, "message": "User approved."},
        }
    else:
        return {
            **state,
            "status": "failed",
            "current_node": "approval",
            "error": "User rejected the pending action.",
            "result": {"approval": False, "message": "User rejected."},
        }


# ─────────────────────────────────────────────────────────────────────────────
# Routing Logic
# ─────────────────────────────────────────────────────────────────────────────

def should_use_tool(state: WorkflowState) -> Literal["tool_node", "format_response"]:
    """Route after chat_node: go to tool_node if status is calling_tool, else format_response."""
    if state.get("status") == "calling_tool":
        return "tool_node"
    return "format_response"


def should_format_or_retry(state: WorkflowState) -> Literal["format_response", "chat_node"]:
    """Route after tool_node: always format_response (retry is handled by the chat node)."""
    return "format_response"


def should_continue_or_end(state: WorkflowState) -> Literal["format_response", "__end__"]:
    """Route after format_response: always end."""
    return "__end__"


# ─────────────────────────────────────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_llm():
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=0.7,
    )


def build_basic_workflow() -> StateGraph:
    """
    Builds and compiles the basic workflow graph.

    Graph structure:
        chat_node ──┬── [calling_tool] ──→ tool_node ──→ format_response ── END
                    └── [otherwise] ───────→ format_response ── END

    Returns the compiled StateGraph ready to be invoked with .ainvoke().
    """
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("chat_node", chat_node)
    workflow.add_node("tool_node", tool_node)
    workflow.add_node("format_response", format_response_node)
    workflow.add_node("approval_node", approval_node)

    # Set entry point
    workflow.set_entry_point("chat_node")

    # Edges
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

    # Approval subgraph edge (triggered when chat_node sets pending_approval)
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
# Checkpointer (Django persistence)
# ─────────────────────────────────────────────────────────────────────────────

_checkpointer: "DjangoSaver | None" = None


def get_checkpointer() -> "DjangoSaver":
    global _checkpointer
    if _checkpointer is None:
        from langgraph.checkpoint.django.saver import DjangoSaver
        _checkpointer = DjangoSaver()
    return _checkpointer


# ─────────────────────────────────────────────────────────────────────────────
# Compiled Graph Singleton
# ─────────────────────────────────────────────────────────────────────────────

_compiled: StateGraph | None = None


def get_compiled_graph() -> StateGraph:
    """Returns the compiled workflow graph (singleton)."""
    global _compiled
    if _compiled is None:
        builder = build_basic_workflow()
        _compiled = builder.compile(checkpointer=get_checkpointer())
    return _compiled


# ─────────────────────────────────────────────────────────────────────────────
# Public Invocation API
# ─────────────────────────────────────────────────────────────────────────────

def run_workflow(
    query: str,
    context: dict | None = None,
    resume_value: str | None = None,
) -> dict:
    """
    Synchronous entrypoint to run the basic workflow.

    Args:
        query:        User query string.
        context:      Optional dict of additional context.
        resume_value: Pass a value to resume from a pending_approval state.

    Returns:
        The final WorkflowState dict.
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

    # Run with a MemorySaver in-process when no DB checkpointer is configured
    try:
        result = graph.invoke(initial_input, config=config)
    except Exception:
        # Fallback to in-memory checkpointer if DB not ready
        mem = MemorySaver()
        builder = build_basic_workflow()
        mem_graph = builder.compile(checkpointer=mem)
        result = mem_graph.invoke(initial_input, config=config)

    return result
