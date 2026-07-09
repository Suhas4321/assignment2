"""Chat / LangGraph agent endpoints."""
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agent.graph import run_agent
from db import crud
from db.database import get_db
from schemas.interaction import AgentChatRequest, AgentChatResponse

router = APIRouter(prefix="/agent", tags=["Agent"])

# In-memory session store for multi-turn form_data / hcp context
# (sufficient for demo; production would use Redis)
_SESSIONS: Dict[str, Dict[str, Any]] = {}


@router.post("/chat", response_model=AgentChatResponse)
def chat(payload: AgentChatRequest, db: Session = Depends(get_db)):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    session_id = payload.session_id or "default"
    session = _SESSIONS.setdefault(
        session_id,
        {
            "history": [],
            "form_data": {},
            "current_hcp": None,
            "interaction_id": None,
        },
    )

    current_hcp = session.get("current_hcp")
    if payload.hcp_id:
        hcp = crud.get_hcp(db, payload.hcp_id)
        if hcp:
            current_hcp = {
                "id": hcp.id,
                "name": hcp.name,
                "specialty": hcp.specialty,
                "hospital": hcp.hospital,
                "location": hcp.location,
            }

    try:
        result = run_agent(
            payload.message.strip(),
            session_id=session_id,
            rep_id=payload.rep_id or "REP-001",
            current_hcp=current_hcp,
            form_data=session.get("form_data") or {},
            history=session.get("history") or [],
            interaction_id=session.get("interaction_id"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {e}") from e

    # Persist session context
    session["history"].append({"role": "user", "content": payload.message.strip()})
    session["history"].append({"role": "assistant", "content": result["reply"]})
    # Keep last 20 turns
    session["history"] = session["history"][-40:]
    if result.get("form_data"):
        session["form_data"] = {**(session.get("form_data") or {}), **result["form_data"]}
    if result.get("current_hcp"):
        session["current_hcp"] = result["current_hcp"]
    if result.get("interaction_id"):
        session["interaction_id"] = result["interaction_id"]

    return AgentChatResponse(
        reply=result["reply"],
        form_data=session.get("form_data") or result.get("form_data"),
        tool_calls=result.get("tool_calls") or [],
        current_hcp=session.get("current_hcp"),
        interaction_id=session.get("interaction_id"),
    )


@router.post("/chat/reset")
def reset_chat(session_id: str = "default"):
    _SESSIONS.pop(session_id, None)
    return {"status": "ok", "session_id": session_id}


@router.get("/tools")
def list_tools():
    """Document the 5 LangGraph tools for evaluators / video walkthrough."""
    return {
        "tools": [
            {
                "name": "log_interaction",
                "description": (
                    "Captures interaction data from natural language. "
                    "Uses LLM for entity extraction + summarization, then persists to DB."
                ),
                "mandatory": True,
            },
            {
                "name": "edit_interaction",
                "description": (
                    "Modifies a previously logged interaction by id with JSON field updates."
                ),
                "mandatory": True,
            },
            {
                "name": "search_hcp",
                "description": "Search/lookup Healthcare Professionals by name, specialty, location.",
                "mandatory": False,
            },
            {
                "name": "get_interaction_history",
                "description": "Fetch previous interactions with an HCP for pre-call context.",
                "mandatory": False,
            },
            {
                "name": "schedule_follow_up",
                "description": "Create a follow-up action item / next-step task after an interaction.",
                "mandatory": False,
            },
        ]
    }
