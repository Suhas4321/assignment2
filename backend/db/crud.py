import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from db import models


# ─── HCP ──────────────────────────────────────────────────────────────────────

def _name_tokens(text: str) -> List[str]:
    stop = {"dr", "md", "mrs", "mr", "ms", "prof", "and", "with", "the"}
    return [
        t
        for t in re.sub(r"[^\w\s]", " ", (text or "").lower()).split()
        if len(t) > 1 and t not in stop
    ]


def search_hcps(
    db: Session,
    query: Optional[str] = None,
    specialty: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 20,
) -> List[models.HCP]:
    """Search HCPs. Prefer name matches; rank exact/full-name hits first."""
    q = db.query(models.HCP)
    if specialty:
        q = q.filter(models.HCP.specialty.ilike(f"%{specialty}%"))
    if location:
        q = q.filter(models.HCP.location.ilike(f"%{location}%"))

    if not query or not query.strip():
        return q.order_by(models.HCP.name).limit(limit).all()

    raw = query.strip()
    tokens = _name_tokens(raw)
    # Soft OR on name tokens so "Dr. Arun Chopra" still finds the row
    if tokens:
        name_clauses = [models.HCP.name.ilike(f"%{t}%") for t in tokens]
        other_clauses = []
        for t in tokens:
            like = f"%{t}%"
            other_clauses.extend(
                [
                    models.HCP.specialty.ilike(like),
                    models.HCP.hospital.ilike(like),
                    models.HCP.location.ilike(like),
                ]
            )
        q = q.filter(or_(*(name_clauses + other_clauses)))
    else:
        like = f"%{raw}%"
        q = q.filter(
            or_(
                models.HCP.name.ilike(like),
                models.HCP.specialty.ilike(like),
                models.HCP.hospital.ilike(like),
                models.HCP.location.ilike(like),
            )
        )

    rows = q.all()

    # Rank: more name-token hits first, then alphabetical
    def score(h: models.HCP) -> tuple:
        n = (h.name or "").lower()
        hits = sum(1 for t in tokens if t in n) if tokens else 0
        exact = 1 if raw.lower().replace(".", "") in n.replace(".", "") else 0
        return (-exact, -hits, h.name or "")

    rows.sort(key=score)
    return rows[:limit]


def get_hcp(db: Session, hcp_id: int) -> Optional[models.HCP]:
    return db.query(models.HCP).filter(models.HCP.id == hcp_id).first()


def get_hcp_by_name(db: Session, name: str) -> Optional[models.HCP]:
    """
    Resolve a single HCP from a name string with accuracy priority:
    1) Exact case-insensitive match
    2) Full name contains all tokens (e.g. Arun + Chopra)
    3) Best single ranked search hit (only if score is strong)
    """
    if not name or not str(name).strip():
        return None
    raw = str(name).strip()

    # Exact
    exact = db.query(models.HCP).filter(models.HCP.name.ilike(raw)).first()
    if exact:
        return exact

    # Exact without "Dr." prefix noise
    cleaned = re.sub(r"^(dr\.?|prof\.?)\s+", "", raw, flags=re.I).strip()
    if cleaned != raw:
        exact2 = (
            db.query(models.HCP)
            .filter(
                or_(
                    models.HCP.name.ilike(cleaned),
                    models.HCP.name.ilike(f"Dr. {cleaned}"),
                    models.HCP.name.ilike(f"Dr {cleaned}"),
                )
            )
            .first()
        )
        if exact2:
            return exact2

    tokens = _name_tokens(raw)
    if not tokens:
        return None

    # All name tokens must appear in the HCP name (not specialty/hospital)
    candidates = db.query(models.HCP).all()
    strong = []
    for h in candidates:
        n = (h.name or "").lower()
        if all(t in n for t in tokens):
            strong.append(h)
    if len(strong) == 1:
        return strong[0]
    if len(strong) > 1:
        # Prefer longest token overlap / closer length
        strong.sort(key=lambda h: abs(len(h.name) - len(raw)))
        return strong[0]

    # Last resort: ranked search, require at least 2 token hits or 1 unique last name
    ranked = search_hcps(db, query=raw, limit=5)
    if not ranked:
        return None
    top = ranked[0]
    n = (top.name or "").lower()
    hits = sum(1 for t in tokens if t in n)
    if hits >= min(2, len(tokens)):
        return top
    # Single distinctive token (e.g. "Chopra") unique in DB
    if len(tokens) == 1 or hits == 1:
        last = tokens[-1]
        uniq = [h for h in candidates if last in (h.name or "").lower()]
        if len(uniq) == 1:
            return uniq[0]
    return None


def list_hcps(db: Session, skip: int = 0, limit: int = 100) -> List[models.HCP]:
    return db.query(models.HCP).order_by(models.HCP.name).offset(skip).limit(limit).all()


def create_hcp(db: Session, data: Dict[str, Any]) -> models.HCP:
    hcp = models.HCP(**data)
    db.add(hcp)
    db.commit()
    db.refresh(hcp)
    return hcp


# ─── Interactions ─────────────────────────────────────────────────────────────

def create_interaction(db: Session, data: Dict[str, Any]) -> models.Interaction:
    interaction = models.Interaction(**data)
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


def get_interaction(db: Session, interaction_id: int) -> Optional[models.Interaction]:
    return (
        db.query(models.Interaction)
        .options(joinedload(models.Interaction.hcp))
        .filter(models.Interaction.id == interaction_id)
        .first()
    )


def update_interaction(
    db: Session, interaction_id: int, updates: Dict[str, Any]
) -> Optional[models.Interaction]:
    interaction = get_interaction(db, interaction_id)
    if not interaction:
        return None
    for key, value in updates.items():
        if value is not None and hasattr(interaction, key):
            setattr(interaction, key, value)
    interaction.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(interaction)
    return interaction


def get_interactions_for_hcp(
    db: Session, hcp_id: int, limit: int = 20
) -> List[models.Interaction]:
    return (
        db.query(models.Interaction)
        .options(joinedload(models.Interaction.hcp))
        .filter(models.Interaction.hcp_id == hcp_id)
        .order_by(models.Interaction.interaction_date.desc(), models.Interaction.id.desc())
        .limit(limit)
        .all()
    )


def list_interactions(
    db: Session, skip: int = 0, limit: int = 50
) -> List[models.Interaction]:
    return (
        db.query(models.Interaction)
        .options(joinedload(models.Interaction.hcp))
        .order_by(models.Interaction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# ─── Follow-ups ───────────────────────────────────────────────────────────────

def create_follow_up(db: Session, data: Dict[str, Any]) -> models.FollowUp:
    fu = models.FollowUp(**data)
    db.add(fu)
    db.commit()
    db.refresh(fu)
    return fu


def get_follow_ups_for_hcp(db: Session, hcp_id: int) -> List[models.FollowUp]:
    return (
        db.query(models.FollowUp)
        .filter(models.FollowUp.hcp_id == hcp_id)
        .order_by(models.FollowUp.due_date.asc())
        .all()
    )


def list_follow_ups(db: Session, status: Optional[str] = None) -> List[models.FollowUp]:
    q = db.query(models.FollowUp).options(joinedload(models.FollowUp.hcp))
    if status:
        q = q.filter(models.FollowUp.status == status)
    return q.order_by(models.FollowUp.due_date.asc()).all()
