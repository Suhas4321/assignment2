"""
LangGraph agent tools for the HCP CRM module.

Mandatory tools (assignment):
  1. log_interaction  – capture interaction data (+ LLM summarize/extract)
  2. edit_interaction – modify a previously logged interaction

Additional tools:
  3. search_hcp              – lookup HCPs by name/specialty/location
  4. get_interaction_history – prior interactions with an HCP
  5. schedule_follow_up      – create a follow-up task/action item
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq

from config import settings
from db import crud
from db.database import SessionLocal

logger = logging.getLogger(__name__)


def _get_llm(temperature: float = 0.0) -> ChatGroq:
    """Primary model — low temperature for extraction accuracy."""
    model = settings.GROQ_MODEL or "llama-3.1-8b-instant"
    return ChatGroq(
        api_key=settings.GROQ_API_KEY or "not-set",
        model=model,
        temperature=temperature,
    )


def _heuristic_extract(natural_language: str) -> Dict[str, Any]:
    """Fast local extraction — no network. Used offline or when LLM JSON fails.
    Aims to populate every form field when the notes mention them.
    """
    text = natural_language or ""
    low = text.lower()
    name_m = re.search(r"(Dr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)

    # Interaction type
    itype = "Meeting"
    if re.search(r"\bcall\b", low) and not re.search(r"\bmeeting\b", low):
        itype = "Call"
    elif "email" in low:
        itype = "Email"
    elif "conference" in low:
        itype = "Conference"
    elif "visit" in low:
        itype = "Visit"

    # Sentiment
    sentiment = "Neutral"
    if "positive" in low:
        sentiment = "Positive"
    elif "negative" in low:
        sentiment = "Negative"

    # Topics
    topics = text[:500]
    tm = re.search(
        r"(?:discussed|discussion(?:s)?(?: about| on)?|topics?(?: were| was)?)\s+(.+?)(?:\.|;| sentiment| shared| samples| outcomes| follow| attendees|$)",
        text,
        re.I,
    )
    if tm:
        topics = tm.group(1).strip(" ,.")

    # Materials shared
    materials = []
    for m in re.finditer(
        r"(?:shared|materials?\s*(?:shared)?[:\-]?)\s+([A-Za-z0-9 ,/\-]+?)(?:\.|;| samples| sentiment| outcomes| follow|$)",
        text,
        re.I,
    ):
        chunk = m.group(1).strip(" ,.")
        for part in re.split(r",| and ", chunk):
            p = part.strip(" .")
            if p and p.lower() not in ("the", "a", "an"):
                materials.append(p)
    if "brochure" in low and not any("brochure" in x.lower() for x in materials):
        materials.append("Brochures")

    # Samples
    samples = []
    sm = re.search(
        r"samples?\s*(?:distributed|given|provided)?[:\-]?\s*([A-Za-z0-9 ,/\-]+?)(?:\.|;| outcomes| follow| sentiment|$)",
        text,
        re.I,
    )
    if sm:
        for part in re.split(r",| and ", sm.group(1)):
            p = part.strip(" .")
            if p:
                samples.append(p)
    if "starter kit" in low and not samples:
        samples.append("Starter kits")

    # Attendees
    attendees = []
    am = re.search(
        r"attendees?[:\-]?\s*([A-Za-z0-9 ,\.\-]+?)(?:\.|;| topics| discussed| sentiment|$)",
        text,
        re.I,
    )
    if am:
        for part in re.split(r",| and ", am.group(1)):
            p = part.strip(" .")
            if p:
                attendees.append(p)
    if name_m and name_m.group(1) not in attendees:
        attendees = [name_m.group(1)] + attendees

    # Outcomes
    outcomes = None
    om = re.search(
        r"outcomes?[:\-]?\s*(.+?)(?:\.|;| follow|$)",
        text,
        re.I,
    )
    if om:
        outcomes = om.group(1).strip(" .")
    elif "agreed" in low:
        outcomes = "HCP agreed to next steps as discussed"

    # Follow-up
    follow = None
    fm = re.search(
        r"follow[\-\s]?up(?:s| actions?)?[:\-]?\s*(.+?)(?:\.|$)",
        text,
        re.I,
    )
    if fm:
        follow = fm.group(1).strip(" .")
    elif "follow" in low:
        follow = "Schedule follow-up meeting in 2 weeks"

    # Time if mentioned HH:MM
    time_m = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", text)
    interaction_time = f"{int(time_m.group(1)):02d}:{time_m.group(2)}" if time_m else None

    products = []
    for token in ("OncoBoost", "Product X", "Product Y", "CardioMax", "Prodo-X"):
        if token.lower() in low:
            products.append(token)

    return {
        "hcp_name": name_m.group(1) if name_m else None,
        "interaction_type": itype,
        "interaction_date": date.today().isoformat(),
        "interaction_time": interaction_time,
        "attendees": attendees,
        "topics_discussed": topics,
        "products_discussed": products,
        "materials_shared": materials or (["Brochures"] if "brochure" in low else []),
        "samples_distributed": samples,
        "sentiment": sentiment,
        "outcomes": outcomes,
        "follow_up_actions": follow,
        "summary": text[:300],
    }


def _llm_extract_and_summarize(natural_language: str) -> Dict[str, Any]:
    """
    Use the LLM to extract structured interaction fields and produce a summary
    from free-form sales-rep notes. One LLM call max (no slow dual-model retry).
    """
    today = date.today().isoformat()
    system = (
        "You fill a CRM log-interaction form from sales-rep notes. "
        "Return ONLY valid JSON (no markdown) with ALL keys filled when possible:\n"
        "hcp_name — PRIMARY doctor the meeting/call is WITH "
        "(from phrases like 'with Dr. X' / 'met Dr. X'). "
        "Do NOT pick a nurse or secondary attendee as hcp_name.\n"
        "interaction_type (Meeting|Call|Email|Conference|Visit|Other),\n"
        f"interaction_date (YYYY-MM-DD, use {today} if not stated),\n"
        "interaction_time — keep AM/PM if given (e.g. '10:30 AM' or '14:15'),\n"
        "attendees (array of all people including HCP),\n"
        "topics_discussed (string), products_discussed (array),\n"
        "materials_shared (array), samples_distributed (array),\n"
        "sentiment (Positive|Neutral|Negative),\n"
        "outcomes (string), follow_up_actions (string),\n"
        "summary (1-2 sentences).\n"
        "Never invent a doctor name that is not in the notes."
    )


    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("your_"):
        out = _heuristic_extract(natural_language)
        out["_note"] = "Offline heuristic extraction"
        return out

    try:
        llm = _get_llm(temperature=0.1)
        resp = llm.invoke(
            [
                SystemMessage(content=system),
                HumanMessage(content=natural_language),
            ]
        )
        text = (resp.content or "").strip()
        if text.startswith("```"):
            lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
            text = "\n".join(lines)
        # Tolerate trailing prose after JSON
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        return json.loads(text)
    except Exception as e:
        logger.warning("LLM extract failed, using heuristics (no 2nd LLM): %s", e)
        out = _heuristic_extract(natural_language)
        out["_error"] = str(e)
        return out


def _parse_date(value: Optional[str]) -> date:
    """Prefer real/current dates — ignore wrong years hallucinated by the LLM."""
    if not value:
        return date.today()
    try:
        d = datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        # If model invents a year far from now, use today (keep month/day if same year)
        if abs(d.year - date.today().year) > 0:
            return date.today()
        return d
    except ValueError:
        return date.today()


def _parse_time(value: Optional[str]) -> Optional[str]:
    """
    Normalize times to 24h HH:MM for HTML <input type="time">.
    Accepts '10:30 AM', '2:15 PM', '14:15', '10:30'.
    """
    if not value:
        return None
    s = str(value).strip()
    m = re.search(
        r"\b(\d{1,2}):(\d{2})\s*(a\.?m\.?|p\.?m\.?)?\b",
        s,
        re.I,
    )
    if not m:
        m2 = re.search(r"\b(\d{1,2})\s*(a\.?m\.?|p\.?m\.?)\b", s, re.I)
        if not m2:
            return None
        hour, ampm = int(m2.group(1)), m2.group(2).lower().replace(".", "")
        minute = 0
    else:
        hour, minute = int(m.group(1)), int(m.group(2))
        ampm = (m.group(3) or "").lower().replace(".", "")
    if ampm.startswith("p") and hour < 12:
        hour += 12
    if ampm.startswith("a") and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def _primary_hcp_name_from_notes(notes: str) -> Optional[str]:
    """
    Extract the PRIMARY doctor the meeting is WITH — not random attendees.
    Patterns: 'with Dr. X', 'met Dr. X', 'Meeting with Dr. X', 'Call with Dr. X'
    """
    text = notes or ""
    patterns = [
        r"(?:meeting|call|visit|email|conference)\s+with\s+(Dr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:met|meet|met with|spoke with|visited)\s+(Dr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:with)\s+(Dr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"^(Dr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            name = m.group(1).strip()
            # Normalize "Dr " → "Dr."
            name = re.sub(r"^Dr\s+", "Dr. ", name, flags=re.I)
            if not name.lower().startswith("dr"):
                name = "Dr. " + name
            return name
    # Fallback: first Dr. Full Name in text
    m = re.search(r"(Dr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
    if m:
        name = m.group(1).strip()
        name = re.sub(r"^Dr\s+", "Dr. ", name, flags=re.I)
        return name
    return None


def _as_str(value: Any) -> Optional[str]:
    """LLM sometimes returns a list for text fields — coerce to string."""
    if value is None:
        return None
    if isinstance(value, list):
        return "; ".join(str(x) for x in value if x is not None)
    return str(value)


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        # JSON array string
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        return [x.strip() for x in s.split(",") if x.strip()]
    return [value]


# ─── Tool 1: Log Interaction ──────────────────────────────────────────────────

@tool
def log_interaction(
    notes: str,
    hcp_id: Optional[int] = None,
    hcp_name: Optional[str] = None,
    rep_id: str = "REP-001",
    interaction_type: Optional[str] = None,
) -> str:
    """
    Log a new HCP interaction from natural-language notes.
    Uses the LLM to extract entities (HCP, products, sentiment, outcomes) and
    generate a professional summary, then persists the interaction to the database.

    Args:
        notes: Free-form description of the meeting/call from the sales rep.
        hcp_id: Optional known HCP id. If omitted, resolves from hcp_name or notes.
        hcp_name: Optional HCP name to search if hcp_id not provided.
        rep_id: Sales representative identifier.
        interaction_type: Optional override (Meeting, Call, Email, Conference, Visit).
    """
    db = SessionLocal()
    try:
        extracted = _llm_extract_and_summarize(notes)

        # ── Accuracy-first HCP resolution ──────────────────────────────────
        # Primary doctor = who the meeting is WITH (from notes), NOT attendees
        # and NOT a stale preselected hcp_id from a previous chat turn.
        primary_from_notes = _primary_hcp_name_from_notes(notes)
        name_hint = (
            primary_from_notes
            or hcp_name
            or extracted.get("hcp_name")
        )
        # Prefer structured extract only if notes primary missing
        if extracted.get("hcp_name") and not primary_from_notes:
            name_hint = extracted.get("hcp_name")

        hcp = None
        # 1) Resolve by name from notes (source of truth)
        if name_hint:
            hcp = crud.get_hcp_by_name(db, str(name_hint))

        # 2) Only trust provided hcp_id if it matches the named doctor
        if hcp_id:
            by_id = crud.get_hcp(db, hcp_id)
            if by_id:
                if hcp is None:
                    hcp = by_id
                elif by_id.id != hcp.id:
                    # Stale/wrong preselection — keep name-resolved HCP
                    logger.info(
                        "Ignoring hcp_id=%s (%s); notes name resolved to %s",
                        hcp_id,
                        by_id.name,
                        hcp.name,
                    )

        if not hcp:
            candidates = crud.search_hcps(db, query=name_hint or notes[:60], limit=5)
            if candidates:
                listing = "; ".join(
                    f"id={c.id} {c.name} ({c.specialty}, {c.hospital})"
                    for c in candidates
                )
                return json.dumps(
                    {
                        "status": "needs_hcp",
                        "message": (
                            f"Could not uniquely identify HCP "
                            f"'{name_hint or 'from notes'}'. "
                            f"Candidates: {listing}. "
                            "Please confirm the HCP name exactly as in the directory."
                        ),
                        "candidates": [
                            {"id": c.id, "name": c.name, "specialty": c.specialty}
                            for c in candidates
                        ],
                        "extracted": extracted,
                    }
                )
            return json.dumps(
                {
                    "status": "error",
                    "message": (
                        f"No HCP found matching '{name_hint or 'notes'}'. "
                        "Use search_hcp with the exact last name, then retry."
                    ),
                    "extracted": extracted,
                }
            )

        itype = (
            interaction_type
            or extracted.get("interaction_type")
            or "Meeting"
        )
        # Time: prefer AM/PM parse from raw notes, then extract field
        time_val = _parse_time(notes) or _parse_time(extracted.get("interaction_time"))
        data = {
            "hcp_id": hcp.id,
            "rep_id": rep_id,
            "interaction_type": _as_str(itype) or "Meeting",
            "interaction_date": _parse_date(extracted.get("interaction_date")),
            "interaction_time": time_val,
            "attendees": _as_list(extracted.get("attendees")),
            "topics_discussed": _as_str(extracted.get("topics_discussed")),
            "materials_shared": _as_list(extracted.get("materials_shared")),
            "samples_distributed": _as_list(extracted.get("samples_distributed")),
            "products_discussed": _as_list(extracted.get("products_discussed")),
            "sentiment": _as_str(extracted.get("sentiment")) or "Neutral",
            "outcomes": _as_str(extracted.get("outcomes")),
            "follow_up_actions": _as_str(extracted.get("follow_up_actions")),
            "summary": _as_str(extracted.get("summary")),
            "raw_chat_input": notes,
        }
        interaction = crud.create_interaction(db, data)

        result = {
            "status": "success",
            "message": f"Interaction #{interaction.id} logged for {hcp.name}.",
            "interaction_id": interaction.id,
            "hcp": {
                "id": hcp.id,
                "name": hcp.name,
                "specialty": hcp.specialty,
                "hospital": hcp.hospital,
            },
            "form_data": {
                "hcp_id": hcp.id,
                "hcp_name": hcp.name,
                "interaction_type": interaction.interaction_type,
                "interaction_date": str(interaction.interaction_date),
                "interaction_time": interaction.interaction_time,
                "attendees": interaction.attendees or [],
                "topics_discussed": interaction.topics_discussed,
                "materials_shared": interaction.materials_shared or [],
                "samples_distributed": interaction.samples_distributed or [],
                "products_discussed": interaction.products_discussed or [],
                "sentiment": interaction.sentiment,
                "outcomes": interaction.outcomes,
                "follow_up_actions": interaction.follow_up_actions,
                "summary": interaction.summary,
            },
        }
        return json.dumps(result)
    except Exception as e:
        logger.exception("log_interaction failed")
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()


# ─── Tool 2: Edit Interaction ─────────────────────────────────────────────────

@tool
def edit_interaction(
    interaction_id: int,
    updates_json: str,
) -> str:
    """
    Edit a previously logged interaction.
    Pass a JSON object of fields to update. Allowed keys:
    interaction_type, interaction_date, interaction_time, attendees,
    topics_discussed, materials_shared, samples_distributed, products_discussed,
    sentiment, outcomes, follow_up_actions, summary, hcp_id.

    Args:
        interaction_id: ID of the interaction to modify.
        updates_json: JSON string of field updates, e.g.
            '{"sentiment":"Positive","outcomes":"Agreed to pilot"}'
    """
    db = SessionLocal()
    try:
        try:
            updates = json.loads(updates_json) if isinstance(updates_json, str) else updates_json
        except json.JSONDecodeError:
            return json.dumps(
                {"status": "error", "message": "updates_json must be valid JSON"}
            )

        # Coerce date string
        if "interaction_date" in updates and isinstance(updates["interaction_date"], str):
            updates["interaction_date"] = _parse_date(updates["interaction_date"])

        allowed = {
            "hcp_id",
            "rep_id",
            "interaction_type",
            "interaction_date",
            "interaction_time",
            "attendees",
            "topics_discussed",
            "materials_shared",
            "samples_distributed",
            "products_discussed",
            "sentiment",
            "outcomes",
            "follow_up_actions",
            "summary",
        }
        clean = {k: v for k, v in updates.items() if k in allowed}
        if not clean:
            return json.dumps(
                {"status": "error", "message": "No valid fields to update."}
            )

        interaction = crud.update_interaction(db, interaction_id, clean)
        if not interaction:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Interaction #{interaction_id} not found.",
                }
            )

        hcp = interaction.hcp
        return json.dumps(
            {
                "status": "success",
                "message": f"Interaction #{interaction.id} updated.",
                "interaction_id": interaction.id,
                "updated_fields": list(clean.keys()),
                "form_data": {
                    "hcp_id": interaction.hcp_id,
                    "hcp_name": hcp.name if hcp else None,
                    "interaction_type": interaction.interaction_type,
                    "interaction_date": str(interaction.interaction_date),
                    "interaction_time": interaction.interaction_time,
                    "attendees": interaction.attendees or [],
                    "topics_discussed": interaction.topics_discussed,
                    "materials_shared": interaction.materials_shared or [],
                    "samples_distributed": interaction.samples_distributed or [],
                    "products_discussed": interaction.products_discussed or [],
                    "sentiment": interaction.sentiment,
                    "outcomes": interaction.outcomes,
                    "follow_up_actions": interaction.follow_up_actions,
                    "summary": interaction.summary,
                },
            }
        )
    except Exception as e:
        logger.exception("edit_interaction failed")
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()


# ─── Tool 3: Search HCP ───────────────────────────────────────────────────────

@tool
def search_hcp(
    query: str = "",
    specialty: Optional[str] = None,
    location: Optional[str] = None,
) -> str:
    """
    Search for Healthcare Professionals by name, specialty, hospital, or location.
    Use this before logging an interaction when the HCP is not yet identified.

    Args:
        query: Free-text search (name, hospital, etc.).
        specialty: Optional specialty filter (e.g. Oncology, Cardiology).
        location: Optional city/region filter.
    """
    db = SessionLocal()
    try:
        results = crud.search_hcps(
            db, query=query or None, specialty=specialty, location=location, limit=15
        )
        if not results:
            return json.dumps(
                {
                    "status": "empty",
                    "message": f"No HCPs found for query='{query}'.",
                    "results": [],
                }
            )
        payload = [
            {
                "id": h.id,
                "name": h.name,
                "specialty": h.specialty,
                "hospital": h.hospital,
                "location": h.location,
                "email": h.email,
            }
            for h in results
        ]
        return json.dumps(
            {
                "status": "success",
                "count": len(payload),
                "results": payload,
                "message": f"Found {len(payload)} HCP(s).",
            }
        )
    except Exception as e:
        logger.exception("search_hcp failed")
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()


# ─── Tool 4: Get Interaction History ──────────────────────────────────────────

@tool
def get_interaction_history(
    hcp_id: Optional[int] = None,
    hcp_name: Optional[str] = None,
    limit: int = 10,
) -> str:
    """
    Fetch previous interactions with an HCP for context before a visit/call.
    Provide either hcp_id or hcp_name.

    Args:
        hcp_id: HCP database id.
        hcp_name: HCP name to look up if id unknown.
        limit: Max number of past interactions to return (default 10).
    """
    db = SessionLocal()
    try:
        hcp = None
        if hcp_id:
            hcp = crud.get_hcp(db, hcp_id)
        elif hcp_name:
            hcp = crud.get_hcp_by_name(db, hcp_name)

        if not hcp:
            return json.dumps(
                {
                    "status": "error",
                    "message": "HCP not found. Use search_hcp first.",
                }
            )

        rows = crud.get_interactions_for_hcp(db, hcp.id, limit=limit)
        history = [
            {
                "id": r.id,
                "type": r.interaction_type,
                "date": str(r.interaction_date),
                "sentiment": r.sentiment,
                "topics": r.topics_discussed,
                "outcomes": r.outcomes,
                "summary": r.summary,
                "products": r.products_discussed or [],
                "follow_up": r.follow_up_actions,
            }
            for r in rows
        ]
        return json.dumps(
            {
                "status": "success",
                "hcp": {
                    "id": hcp.id,
                    "name": hcp.name,
                    "specialty": hcp.specialty,
                    "hospital": hcp.hospital,
                },
                "count": len(history),
                "history": history,
                "message": (
                    f"{len(history)} past interaction(s) for {hcp.name}."
                    if history
                    else f"No prior interactions for {hcp.name}."
                ),
            }
        )
    except Exception as e:
        logger.exception("get_interaction_history failed")
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()


# ─── Tool 5: Schedule Follow-up ───────────────────────────────────────────────

@tool
def schedule_follow_up(
    title: str,
    hcp_id: Optional[int] = None,
    hcp_name: Optional[str] = None,
    description: Optional[str] = None,
    due_in_days: int = 14,
    interaction_id: Optional[int] = None,
    rep_id: str = "REP-001",
) -> str:
    """
    Create a follow-up action item / next-step task after an HCP interaction.
    Stores a database record (no external email is sent).

    Args:
        title: Short title for the follow-up (e.g. "Send OncoBoost Phase III PDF").
        hcp_id: HCP id.
        hcp_name: HCP name if id unknown.
        description: Optional longer description.
        due_in_days: Days from today until due (default 14).
        interaction_id: Optional linked interaction id.
        rep_id: Sales rep identifier.
    """
    db = SessionLocal()
    try:
        hcp = None
        if hcp_id:
            hcp = crud.get_hcp(db, hcp_id)
        elif hcp_name:
            hcp = crud.get_hcp_by_name(db, hcp_name)

        if not hcp:
            return json.dumps(
                {
                    "status": "error",
                    "message": "HCP not found. Provide hcp_id or a known hcp_name.",
                }
            )

        due = date.today() + timedelta(days=max(0, due_in_days or 14))
        fu = crud.create_follow_up(
            db,
            {
                "hcp_id": hcp.id,
                "interaction_id": interaction_id,
                "rep_id": rep_id,
                "title": title,
                "description": description,
                "due_date": due,
                "status": "pending",
            },
        )
        return json.dumps(
            {
                "status": "success",
                "message": f"Follow-up scheduled for {hcp.name} on {due.isoformat()}.",
                "follow_up": {
                    "id": fu.id,
                    "title": fu.title,
                    "description": fu.description,
                    "due_date": str(fu.due_date),
                    "status": fu.status,
                    "hcp_id": hcp.id,
                    "hcp_name": hcp.name,
                    "interaction_id": interaction_id,
                },
            }
        )
    except Exception as e:
        logger.exception("schedule_follow_up failed")
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()


# Export tool list for the graph
ALL_TOOLS = [
    log_interaction,
    edit_interaction,
    search_hcp,
    get_interaction_history,
    schedule_follow_up,
]

TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}
