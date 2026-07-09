"""
LangGraph agent graph for the AI-First CRM HCP module.

Flow:
  START → agent (router/planner with tool-calling LLM)
        → (if tool_calls) tools → agent  (ReAct loop, max steps via recursion)
        → respond → END
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph

from agent.state import AgentState
from agent.nodes import agent_node, respond_node, tools_node

logger = logging.getLogger(__name__)


def _should_continue(state: AgentState) -> str:
    """Route: if the last message has tool_calls → tools, else → respond."""
    messages = state.get("messages") or []
    if not messages:
        return "respond"
    last = messages[-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return "respond"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("respond", respond_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        _should_continue,
        {"tools": "tools", "respond": "respond"},
    )
    # One tool round then format reply (keeps demo simple & avoids offline loops)
    graph.add_edge("tools", "respond")
    graph.add_edge("respond", END)

    return graph.compile()


# Module-level compiled graph (lazy-ish singleton)
_APP = None


def get_agent_app():
    global _APP
    if _APP is None:
        _APP = build_graph()
    return _APP


def run_agent(
    message: str,
    *,
    session_id: str = "default",
    rep_id: str = "REP-001",
    current_hcp: Optional[Dict[str, Any]] = None,
    form_data: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, str]]] = None,
    interaction_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Invoke the LangGraph agent for one user turn.

    Returns dict with reply, form_data, tools_used, current_hcp, interaction_id.
    """
    app = get_agent_app()

    messages = []
    for h in history or []:
        role = h.get("role")
        content = h.get("content") or ""
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=message))

    initial: AgentState = {
        "messages": messages,
        "rep_id": rep_id,
        "session_id": session_id,
        "current_hcp": current_hcp,
        "form_data": form_data or {},
        "tool_output": None,
        "tools_used": [],
        "interaction_id": interaction_id,
        "final_response": "",
    }

    # Cap recursion so multi-tool chains don't loop forever
    result = app.invoke(initial, config={"recursion_limit": 12})

    # Collect tool call metadata for the frontend
    tool_calls_meta: List[Dict[str, Any]] = []
    for name in result.get("tools_used") or []:
        tool_calls_meta.append({"tool": name})

    reply = result.get("final_response") or ""
    if not reply:
        # Fallback: last AI message content
        for m in reversed(result.get("messages") or []):
            if isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
                reply = m.content
                break
        if not reply:
            reply = "Done."

    return {
        "reply": reply,
        "form_data": result.get("form_data") or {},
        "tool_calls": tool_calls_meta,
        "tools_used": result.get("tools_used") or [],
        "current_hcp": result.get("current_hcp"),
        "interaction_id": result.get("interaction_id"),
        "tool_output": result.get("tool_output"),
    }
