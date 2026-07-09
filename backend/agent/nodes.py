"""LangGraph nodes: agent (router/planner) and tools executor."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_groq import ChatGroq

from agent.state import AgentState
from agent.tools import ALL_TOOLS, TOOLS_BY_NAME
from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI assistant for a life-sciences field CRM.
Help sales reps log interactions with Healthcare Professionals (HCPs).

Tools:
1. search_hcp – lookup by name/specialty/location
2. log_interaction – log from free-text notes (extracts form fields + summary)
3. edit_interaction – modify an existing interaction by id
4. get_interaction_history – past interactions for an HCP
5. schedule_follow_up – create a follow-up task

CRITICAL accuracy rules:
- The PRIMARY HCP is the doctor the meeting/call is WITH (e.g. "Meeting with Dr. Arun Chopra").
- Attendees may include nurses or other names — do NOT treat them as the primary HCP.
- ALWAYS pass hcp_name on log_interaction using the primary doctor from the notes (exact spelling).
- Do NOT reuse a pre-selected HCP from context if the notes name a different doctor.
- Prefer: search_hcp(query="<exact last name or full name>") then log_interaction(notes=..., hcp_name="Dr. ...").
- For times, preserve AM/PM from the user (e.g. 10:30 AM, 2:15 PM).
- Only schedule_follow_up when the user mentions follow-up / next steps.
- Be concise. Accuracy over speed — never invent an HCP name.

rep_id defaults from context.
"""


def _build_llm(bind_tools: bool = True) -> Any:
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("your_"):
        return None
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL or "llama-3.1-8b-instant",
        temperature=0.0,  # accuracy over creativity
    )
    if bind_tools:
        return llm.bind_tools(ALL_TOOLS)
    return llm


def _context_block(state: AgentState) -> str:
    parts = [f"rep_id: {state.get('rep_id') or 'REP-001'}"]
    hcp = state.get("current_hcp")
    if hcp:
        parts.append(
            f"preselected_hcp: id={hcp.get('id')} name={hcp.get('name')} "
            f"specialty={hcp.get('specialty')}"
        )
    fd = state.get("form_data") or {}
    if fd:
        parts.append(f"current_form_data: {json.dumps(fd)[:500]}")
    if state.get("interaction_id"):
        parts.append(f"last_interaction_id: {state['interaction_id']}")
    return "\n".join(parts)


def agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Router / planner node.
    Invokes the LLM with tools bound; returns an AIMessage that may contain tool_calls.
    """
    llm = _build_llm(bind_tools=True)
    messages = list(state.get("messages") or [])
    sys = SystemMessage(content=SYSTEM_PROMPT + "\n\nContext:\n" + _context_block(state))

    if llm is None:
        # Offline / no API key path – deterministic heuristic router
        return _offline_agent(state)

    try:
        response = llm.invoke([sys] + messages)
        return {"messages": [response]}
    except Exception as e:
        logger.warning("Primary model failed (%s); trying fallback", e)
        try:
            fallback = ChatGroq(
                api_key=settings.GROQ_API_KEY,
                model=settings.GROQ_FALLBACK_MODEL,
                temperature=0.2,
            ).bind_tools(ALL_TOOLS)
            response = fallback.invoke([sys] + messages)
            return {"messages": [response]}
        except Exception as e2:
            logger.error("Fallback model failed: %s", e2)
            # Degrade to offline heuristic
            return _offline_agent(state, error=str(e2))


def _offline_agent(state: AgentState, error: Optional[str] = None) -> Dict[str, Any]:
    """
    Simple keyword-based tool routing when Groq is unavailable.
    Still exercises all 5 tools so the demo works offline.
    """
    messages = state.get("messages") or []
    last_user = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage) or (
            isinstance(m, dict) and m.get("role") == "user"
        ):
            last_user = m.content if hasattr(m, "content") else m.get("content", "")
            break
        if hasattr(m, "type") and m.type == "human":
            last_user = m.content
            break

    text = (last_user or "").lower()
    rep_id = state.get("rep_id") or "REP-001"
    hcp = state.get("current_hcp") or {}
    hcp_id = hcp.get("id")
    hcp_name = hcp.get("name")

    tool_calls = []

    def tc(name: str, args: dict, id_: str) -> dict:
        return {"name": name, "args": args, "id": id_, "type": "tool_call"}

    # Prefer logging when user describes a visit/meeting (even if "follow up" is mentioned)
    is_log_note = any(
        k in text
        for k in (
            "met ",
            "met dr",
            "discussed",
            "visited",
            "called ",
            "call with",
            "meeting with",
            "log:",
            "logged",
        )
    )

    if (not is_log_note) and any(
        k in text for k in ("search", "find doctor", "find hcp", "look up", "who is")
    ):
        q = last_user
        for prefix in ("search for", "search", "find", "look up", "who is"):
            if prefix in text:
                idx = text.index(prefix) + len(prefix)
                q = last_user[idx:].strip(" :,-")
                break
        tool_calls.append(tc("search_hcp", {"query": q or last_user}, "tc_search"))
    elif (not is_log_note) and any(
        k in text
        for k in ("history", "past interaction", "previous meeting", "prior visit")
    ):
        args: Dict[str, Any] = {"limit": 10}
        if hcp_id:
            args["hcp_id"] = hcp_id
        elif hcp_name:
            args["hcp_name"] = hcp_name
        else:
            args["hcp_name"] = last_user
        tool_calls.append(tc("get_interaction_history", args, "tc_hist"))
    elif (not is_log_note) and any(
        k in text for k in ("follow-up", "follow up", "schedule", "remind me", "next step")
    ):
        title = last_user[:120]
        args = {
            "title": title,
            "rep_id": rep_id,
            "due_in_days": 14,
        }
        if hcp_id:
            args["hcp_id"] = hcp_id
        elif hcp_name:
            args["hcp_name"] = hcp_name
        if state.get("interaction_id"):
            args["interaction_id"] = state["interaction_id"]
        tool_calls.append(tc("schedule_follow_up", args, "tc_fu"))
    elif (not is_log_note) and any(
        k in text for k in ("edit", "update interaction", "change sentiment", "modify")
    ):
        iid = state.get("interaction_id")
        m = re.search(r"(?:interaction\s*#?|#)\s*(\d+)", text)
        if m:
            iid = int(m.group(1))
        if not iid:
            msg = AIMessage(
                content=(
                    "Please specify which interaction to edit "
                    "(e.g. 'edit interaction #3 sentiment to Positive')."
                )
            )
            return {"messages": [msg]}
        updates = {"topics_discussed": last_user}
        if "positive" in text:
            updates["sentiment"] = "Positive"
        elif "negative" in text:
            updates["sentiment"] = "Negative"
        elif "neutral" in text:
            updates["sentiment"] = "Neutral"
        tool_calls.append(
            tc(
                "edit_interaction",
                {"interaction_id": iid, "updates_json": json.dumps(updates)},
                "tc_edit",
            )
        )
    else:
        # Default (and primary demo path): log interaction → fills form blanks
        args = {"notes": last_user, "rep_id": rep_id}
        if hcp_id:
            args["hcp_id"] = hcp_id
        # Pull "Dr. Name" from free text so lookup works offline
        name_match = re.search(
            r"(Dr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", last_user or ""
        )
        if name_match:
            args["hcp_name"] = name_match.group(1)
        elif hcp_name:
            args["hcp_name"] = hcp_name
        tool_calls.append(tc("log_interaction", args, "tc_log"))

    note = ""
    if error:
        note = f" (offline mode: LLM error — {error[:80]})"
    elif not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("your_"):
        note = " (offline mode: set GROQ_API_KEY for full LLM reasoning)"

    if tool_calls:
        msg = AIMessage(
            content=f"I'll handle that for you{note}.",
            tool_calls=tool_calls,
        )
    else:
        msg = AIMessage(content=f"How can I help you log or manage HCP interactions?{note}")
    return {"messages": [msg]}


def tools_node(state: AgentState) -> Dict[str, Any]:
    """
    Execute any tool_calls present on the last AIMessage.
    Updates form_data / current_hcp / interaction_id from tool results.
    """
    messages = state.get("messages") or []
    last = messages[-1] if messages else None
    if not last or not getattr(last, "tool_calls", None):
        return {}

    tool_messages: List[ToolMessage] = []
    tools_used: List[str] = list(state.get("tools_used") or [])
    form_data = dict(state.get("form_data") or {})
    current_hcp = state.get("current_hcp")
    interaction_id = state.get("interaction_id")
    last_output: Any = None

    for call in last.tool_calls:
        name = call.get("name") if isinstance(call, dict) else call["name"]
        args = call.get("args") if isinstance(call, dict) else call["args"]
        call_id = call.get("id") if isinstance(call, dict) else call["id"]

        # Inject rep_id if tool accepts it and missing
        if "rep_id" not in args and name in ("log_interaction", "schedule_follow_up"):
            args = {**args, "rep_id": state.get("rep_id") or "REP-001"}

        # Only inject preselected HCP when the tool call did not name one.
        # Never force a stale hcp_id onto log_interaction — notes are source of truth.
        if current_hcp:
            if name == "get_interaction_history" and "hcp_id" not in args and "hcp_name" not in args:
                args = {**args, "hcp_id": current_hcp.get("id")}
            if name == "schedule_follow_up" and "hcp_id" not in args and "hcp_name" not in args:
                args = {**args, "hcp_id": current_hcp.get("id")}
            # log_interaction: pass hcp_name hint only if model omitted it
            if name == "log_interaction" and "hcp_name" not in args and "hcp_id" not in args:
                if current_hcp.get("name"):
                    args = {**args, "hcp_name": current_hcp.get("name")}

        tool_fn = TOOLS_BY_NAME.get(name)
        if not tool_fn:
            result = json.dumps({"status": "error", "message": f"Unknown tool: {name}"})
        else:
            try:
                result = tool_fn.invoke(args)
            except Exception as e:
                logger.exception("Tool %s failed", name)
                result = json.dumps({"status": "error", "message": str(e)})

        tools_used.append(name)
        last_output = result
        tool_messages.append(ToolMessage(content=str(result), tool_call_id=call_id, name=name))

        # Merge structured side-effects into state
        try:
            parsed = json.loads(result) if isinstance(result, str) else result
        except json.JSONDecodeError:
            parsed = {}

        if isinstance(parsed, dict):
            if parsed.get("form_data"):
                form_data.update(parsed["form_data"])
            if parsed.get("interaction_id"):
                interaction_id = parsed["interaction_id"]
            if parsed.get("hcp"):
                current_hcp = parsed["hcp"]
            if name == "search_hcp" and parsed.get("results"):
                # Prefer single clear match
                if len(parsed["results"]) == 1:
                    current_hcp = parsed["results"][0]
                    form_data["hcp_id"] = current_hcp.get("id")
                    form_data["hcp_name"] = current_hcp.get("name")
            if name == "get_interaction_history" and parsed.get("hcp"):
                current_hcp = parsed["hcp"]

    return {
        "messages": tool_messages,
        "tools_used": tools_used,
        "form_data": form_data,
        "current_hcp": current_hcp,
        "interaction_id": interaction_id,
        "tool_output": last_output,
    }


def _format_tool_reply(state: AgentState, messages: list) -> str:
    """
    Fast reply from tool JSON — no extra LLM round-trip.
    Saves ~1–3s per chat turn vs a second summarization call.
    """
    parts: List[str] = []
    for m in messages:
        if isinstance(m, ToolMessage):
            try:
                data = json.loads(m.content)
                parts.append(data.get("message") or str(m.content)[:200])
            except Exception:
                parts.append(str(m.content)[:200])
    text = " ".join(parts).strip() or "Request processed."
    fd = state.get("form_data") or {}
    if fd.get("hcp_name") or fd.get("summary") or fd.get("sentiment"):
        text += (
            f"\n\nForm updated — HCP: {fd.get('hcp_name') or '—'}; "
            f"Type: {fd.get('interaction_type') or '—'}; "
            f"Sentiment: {fd.get('sentiment') or '—'}."
        )
    return text


def respond_node(state: AgentState) -> Dict[str, Any]:
    """
    Format a final user-facing reply after tools have run (or if no tools needed).
    Uses tool messages directly (no second LLM call) for lower latency.
    """
    messages = state.get("messages") or []
    last = messages[-1] if messages else None

    # Plain assistant reply (no tools) — already done
    if isinstance(last, AIMessage) and not getattr(last, "tool_calls", None):
        content = last.content or "Done."
        return {"final_response": content, "messages": []}

    text = _format_tool_reply(state, messages)
    return {
        "final_response": text,
        "messages": [AIMessage(content=text)],
    }
