from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from schemas.interaction import HCPOut, HCPCreate

router = APIRouter(prefix="/hcps", tags=["HCPs"])


@router.get("", response_model=List[HCPOut])
def list_or_search_hcps(
    q: Optional[str] = Query(None, description="Search name/specialty/hospital/location"),
    specialty: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    if q or specialty or location:
        return crud.search_hcps(db, query=q, specialty=specialty, location=location, limit=limit)
    return crud.list_hcps(db, limit=limit)


@router.get("/{hcp_id}", response_model=HCPOut)
def get_hcp(hcp_id: int, db: Session = Depends(get_db)):
    hcp = crud.get_hcp(db, hcp_id)
    if not hcp:
        raise HTTPException(status_code=404, detail="HCP not found")
    return hcp


@router.post("", response_model=HCPOut, status_code=201)
def create_hcp(payload: HCPCreate, db: Session = Depends(get_db)):
    return crud.create_hcp(db, payload.model_dump())
