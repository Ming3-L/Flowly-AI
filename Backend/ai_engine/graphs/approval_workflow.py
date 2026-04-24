"""
Human-in-the-Loop Approval Workflow

A LangGraph workflow that demonstrates the "Human-in-the-Loop" (HiL) pattern.
At a configurable approval node the graph calls ``interrupt()`` to suspend
execution and wait for an external resume signal (POST /resume).

The key primitives are:

1. ``interrupt()`` — raises ``NodeInterrupt`` and serialises the current
   state so the API can persist it and prompt the user.

2. ``Command(resume=...)`` — the mechanism used by ``.invoke()`` /
   ``.ainvoke()`` on resume to inject the user's decision back into the graph
   and continue execution.

Graph structure
────────────────
::

  entry
    │
    ▼
  draft          → LLM generates a draft response / action plan
    │
    ▼
  approval       → calls interrupt() — graph suspends here
    │
    ▼  (after resume with approved=True)
  execute        → apply the approved action (e.g. call a tool)
    │
    ▼
  format_response → final response formatting → END

  approval ──→ [rejected] ──→ END  (skips execute on rejection)

"""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage  # pyright: ignore[reportMissingImports]
from langchain_core.tools import tool  # pyright: ignore[reportMissingImports]
from langgraph.graph import END, StateGraph
from langgraph.types import Command


# ─────────────────────────────────────────────────────────────────────────────
# State Schema
# ─────────────────────────────────────────────────────────────────────────────

class ApprovalState(TypedDict):
    """State for the approval workflow.

    Fields
    ------
    query        : Original user query.
    context      : Additional context passed at invocation time.
    messages     : Full message history.
    status       : Current workflow status string.
    current_node : Name of the node currently executing.
    draft        : LLM-generated draft before approval.
    approved     : Boolean from resume — True = approved, False = rejected.
    resume_input : Free-text input provided by the user on resume.
    result       : Final output after execution.
    error        : Error message if something fails.
    """
    query: str
    context: dict
    messages: Annotated[list[BaseMessage], "Message history"]
    status: Annotated[str, "Current workflow status"]
    current_node: Annotated[str, "Node currently executing"]
    draft: str
    approved: bool
    resume_input: str
    result: dict | None
    error: str | None


# ─────────────────────────────────────────────────────────────────────────────
# Tool Definitions
# ─────────────────────────────────────────────────────────────────────────────

@tool
def send_email(recipient: str, subject: str, body: str) -> str:
    """
    Send an email. Requires user approval before execution.

    Args:
        recipient: Email address of the recipient.
        subject:   Email subject line.
        body:      Email body text.
    """
    # Placeholder — replace with actual email SDK call (e.g. SendGrid, SMTP)
    return f"[Email] Sent to {recipient}: {subject}"


@tool
def create_calendar_event(
    title: str,
    start_time: str,
    end_time: str,
    attendees: list[str],
) -> str:
    """
    Create a calendar event. Requires user approval before execution.

    Args:
        title:     Title of the event.
        start_time: ISO-8601 start datetime.
        end_time:  ISO-8601 end datetime.
        attendees: List of attendee email addresses.
    """
    # Placeholder — replace with Google Calendar / Outlook API call
    return f"[Calendar] Event '{title}' created for {start_time}–{end_time}"


# ─────────────────────────────────────────────────────────────────────────────
# Node Functions
# ─────────────────────────────────────────────────────────────────────────────

def _llm():
    from ai_engine.workflow import get_chat_model

    return get_chat_model("openai", temperature=0.7, streaming=False)


def entry_node(state: ApprovalState) -> ApprovalState:
    """
    Entry point. Logs the start and immediately transitions to draft_node.
    """
    return {
        **state,
        "status": "thinking",
        "current_node": "entry",
    }


def draft_node(state: ApprovalState) -> ApprovalState:
    """
    Uses the LLM to draft a response or action plan.

    The LLM returns a JSON object with:
        action   : "email" | "calendar" | "respond"
        subject  : email subject  (if action == email)
        recipient: email address   (if action == email)
        body     : email body      (if action == email)
        title    : event title     (if action == calendar)
        start    : start datetime  (if action == calendar)
        end      : end datetime    (if action == calendar)
        attendees: attendee list   (if action == calendar)
        draft    : text to show the user for approval
    """
    llm = _llm()

    system_prompt = (
        "You are a workflow assistant. Given the user's query, decide the next action.\n"
        "Respond with valid JSON:\n"
        '  { "action": "email", "recipient": "...", "subject": "...", "body": "...", "draft": "..." }\n'
        '  { "action": "calendar", "title": "...", "start": "...", "end": "...", "attendees": [], "draft": "..." }\n'
        '  { "action": "respond", "draft": "..." }\n'
        'Always include a "draft" field describing what will happen after approval.'
    )

    ai_msg = ai_msg = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["query"]},
    ])

    import json
    try:
        decision = json.loads(ai_msg.content)
    except Exception:
        decision = {"action": "respond", "draft": ai_msg.content}

    draft = decision.get("draft", "")
    action = decision.get("action", "respond")

    state = {
        **state,
        "messages": state["messages"] + [ai_msg],
        "draft": draft,
        "status": "pending_approval",
        "current_node": "draft",
    }

    # Store action metadata in context so execute_node can pick it up
    state["context"] = {
        **state.get("context", {}),
        "action": action,
        **decision,
    }

    return state


def approval_node(state: ApprovalState) -> ApprovalState | Command:
    """
    Human-in-the-loop node.

    If this node is entered for the first time (approved == None), the graph
    calls ``interrupt()`` to suspend. The API layer catches ``NodeInterrupt``,
    persists the state, and sends a pending_approval SSE event to the frontend.

    On resume the ``Command(resume=...)`` object carries the user's decision
    (approved=True/False and optional resume_input) into the graph as the new
    ``approved`` and ``resume_input`` fields.
    """
    if state["approved"] is None:
        # First time here — suspend and wait for user.
        # interrupt() serialises the current state and raises NodeInterrupt.
        raise Command(
            interrupt={
                "reason": "awaiting_approval",
                "draft": state.get("draft", ""),
                "question": (
                    f"Action requires your approval:\n{state.get('draft', 'Please confirm.')}"
                ),
            }
        )

    # Resume path — approved/rejected value is injected by Command(resume=...)
    return {
        **state,
        "current_node": "approval",
        "status": "running" if state["approved"] else "rejected",
    }


def execute_node(state: ApprovalState) -> ApprovalState:
    """
    Executes the approved action (email, calendar, etc.).
    Only reached when approved=True.
    """
    ctx = state.get("context", {})
    action = ctx.get("action", "respond")

    result_content = ""

    if action == "email":
        result_content = send_email.invoke({
            "recipient": ctx.get("recipient", ""),
            "subject": ctx.get("subject", ""),
            "body": ctx.get("body", ""),
        })

    elif action == "calendar":
        result_content = create_calendar_event.invoke({
            "title": ctx.get("title", ""),
            "start_time": ctx.get("start", ""),
            "end_time": ctx.get("end", ""),
            "attendees": ctx.get("attendees", []),
        })

    else:
        result_content = f"[Response] {state['draft']}"

    tool_msg = AIMessage(content=result_content)

    return {
        **state,
        "messages": state["messages"] + [tool_msg],
        "current_node": "execute",
        "status": "running",
        "result": {"output": result_content},
    }


def format_response_node(state: ApprovalState) -> ApprovalState:
    """
    Final node. Builds a clean user-facing summary.
    """
    draft = state.get("draft", "")
    approved = state.get("approved")

    if approved is False:
        response = (
            "This action was **rejected** by you. "
            "No changes have been made."
        )
    elif approved is True:
        result_output = state.get("result", {}).get("output", "")
        response = f"{draft}\n\n**Result:** {result_output}"
    else:
        response = draft

    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=response)],
        "status": "finished",
        "current_node": "format_response",
        "result": {
            "response": response,
            "draft": draft,
            "approved": approved,
            "query": state["query"],
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Routing
# ─────────────────────────────────────────────────────────────────────────────

def route_from_draft(state: ApprovalState) -> Literal["approval", "format_response"]:
    """
    After draft_node: go to approval if there is something to approve,
    otherwise go straight to format_response (e.g. plain respond action).
    """
    action = state.get("context", {}).get("action", "respond")
    if action in ("email", "calendar"):
        return "approval"
    return "format_response"


def route_from_approval(state: ApprovalState) -> Literal["execute", "__end__"]:
    """
    After approval_node on resume: execute if approved, end if rejected.
    """
    if state.get("approved") is True:
        return "execute"
    return "__end__"


# ─────────────────────────────────────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_approval_workflow() -> StateGraph:
    """
    Builds the approval workflow graph.

    Flow
    ────
    entry ──→ draft ──┬── [email|calendar] ──→ approval ──→ execute ──→ format_response ── END
                      └── [respond] ────────────→ format_response ── END

    The approval node calls interrupt() on first entry and is resumed via
    Command(resume={approved, resume_input}) injected at the API layer.
    """
    workflow = StateGraph(ApprovalState)

    workflow.add_node("entry", entry_node)
    workflow.add_node("draft", draft_node)
    workflow.add_node("approval", approval_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("format_response", format_response_node)

    workflow.set_entry_point("entry")

    workflow.add_edge("entry", "draft")
    workflow.add_conditional_edges("draft", route_from_draft, {
        "approval": "approval",
        "format_response": "format_response",
    })
    workflow.add_conditional_edges("approval", route_from_approval, {
        "execute": "execute",
        "__end__": END,
    })
    workflow.add_edge("execute", "format_response")
    workflow.add_edge("format_response", END)

    return workflow


# ─────────────────────────────────────────────────────────────────────────────
# Checkpointer
# ─────────────────────────────────────────────────────────────────────────────

_checkpointer: "DjangoSaver | None" = None


def get_approval_checkpointer() -> "DjangoSaver":
    global _checkpointer
    if _checkpointer is None:
        from langgraph.checkpoint.django.saver import DjangoSaver
        _checkpointer = DjangoSaver()
    return _checkpointer


# ─────────────────────────────────────────────────────────────────────────────
# Compiled Graph
# ─────────────────────────────────────────────────────────────────────────────

_compiled: StateGraph | None = None


def get_approval_graph() -> StateGraph:
    """
    Returns the compiled approval workflow graph (singleton).
    """
    global _compiled
    if _compiled is None:
        builder = build_approval_workflow()
        _compiled = builder.compile(checkpointer=get_approval_checkpointer())
    return _compiled


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def run_approval_workflow(
    query: str,
    context: dict | None = None,
    approved: bool | None = None,
    resume_input: str = "",
) -> dict:
    """
    Synchronous entrypoint for the approval workflow.

    Args
    ----
    query        : User query string.
    context      : Optional additional context dict.
    approved     : None for first run (triggers interrupt).
                   True/False on resume after user decision.
    resume_input : Free-text input from the user on resume.

    Returns
    -------
    The final ApprovalState dict on normal completion.
    Raises Command(interrupt=...) when awaiting approval.
    """
    graph = get_approval_graph()
    thread_id = "default-approval-thread"

    config = {"configurable": {"thread_id": thread_id}}

    initial_input: ApprovalState = {
        "query": query,
        "context": context or {},
        "messages": [],
        "status": "thinking",
        "current_node": "",
        "draft": "",
        "approved": approved,
        "resume_input": resume_input,
        "result": None,
        "error": None,
    }

    if approved is None:
        # First invoke — will raise NodeInterrupt at the approval node
        result = graph.invoke(initial_input, config=config)
    else:
        # Resume with user's decision
        resume_cmd = Command(resume={"approved": approved, "resume_input": resume_input})
        result = graph.invoke(resume_cmd, config=config)

    return result
