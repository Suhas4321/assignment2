from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from schemas.interaction import (
    InteractionCreate,
    InteractionUpdate,
    InteractionOut,
    FollowUpCreate,
    FollowUpOut,
    SuggestFollowUpsRequest,
)

router = APIRouter(tags=["Interactions"])


@router.get("/interactions", response_model=List[InteractionOut])
def list_interactions(
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    return crud.list_interactions(db, skip=skip, limit=limit)


@router.get("/interactions/{interaction_id}", response_model=InteractionOut)
def get_interaction(interaction_id: int, db: Session = Depends(get_db)):
    row = crud.get_interaction(db, interaction_id)
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return row


@router.post("/interactions", response_model=InteractionOut, status_code=201)
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    hcp = crud.get_hcp(db, payload.hcp_id)
    if not hcp:
        raise HTTPException(status_code=400, detail="Invalid hcp_id")
    data = payload.model_dump()
    if not data.get("interaction_date"):
        data["interaction_date"] = date.today()
    return crud.create_interaction(db, data)


@router.patch("/interactions/{interaction_id}", response_model=InteractionOut)
def update_interaction(
    interaction_id: int,
    payload: InteractionUpdate,
    db: Session = Depends(get_db),
):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    row = crud.update_interaction(db, interaction_id, updates)
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return row


@router.get("/hcps/{hcp_id}/interactions", response_model=List[InteractionOut])
def hcp_interactions(
    hcp_id: int,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    if not crud.get_hcp(db, hcp_id):
        raise HTTPException(status_code=404, detail="HCP not found")
    return crud.get_interactions_for_hcp(db, hcp_id, limit=limit)


# ─── Follow-ups ───────────────────────────────────────────────────────────────

@router.get("/follow-ups", response_model=List[FollowUpOut])
def list_follow_ups(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.list_follow_ups(db, status=status)


@router.post("/follow-ups", response_model=FollowUpOut, status_code=201)
def create_follow_up(payload: FollowUpCreate, db: Session = Depends(get_db)):
    if not crud.get_hcp(db, payload.hcp_id):
        raise HTTPException(status_code=400, detail="Invalid hcp_id")
    return crud.create_follow_up(db, payload.model_dump())


@router.get("/hcps/{hcp_id}/follow-ups", response_model=List[FollowUpOut])
def hcp_follow_ups(hcp_id: int, db: Session = Depends(get_db)):
    if not crud.get_hcp(db, hcp_id):
        raise HTTPException(status_code=404, detail="HCP not found")
    return crud.get_follow_ups_for_hcp(db, hcp_id)


@router.post("/interactions/suggest-followups")
def suggest_followups(payload: SuggestFollowUpsRequest):
    """
    Lightweight rule + template suggestions (also used by form AI chips).
    Full LLM suggestions come through the agent chat.
    """
    suggestions = []
    topics = (payload.topics_discussed or "").lower()
    outcomes = (payload.outcomes or "").lower()
    name = payload.hcp_name or "the HCP"

    suggestions.append(f"Schedule follow-up meeting with {name} in 2 weeks")
    if "phase" in topics or "trial" in topics or "study" in topics:
        suggestions.append("Send clinical trial / Phase data PDF")
    if "efficacy" in topics or "data" in topics:
        suggestions.append("Share latest efficacy dossier")
    if "sample" in topics or "sample" in outcomes:
        suggestions.append("Arrange sample replenishment")
    if "advisory" in topics or "board" in topics:
        suggestions.append(f"Add {name} to advisory board invite list")
    if "brochure" in topics or "material" in topics:
        suggestions.append("Email digital brochure package")
    if not suggestions:
        suggestions.append("Send thank-you note and product overview")

    # de-dupe preserve order
    seen = set()
    unique = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return {"suggestions": unique[:5]}
