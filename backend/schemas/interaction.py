from datetime import date, datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# ─── HCP ──────────────────────────────────────────────────────────────────────

class HCPBase(BaseModel):
    name: str
    specialty: Optional[str] = None
    hospital: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class HCPCreate(HCPBase):
    pass


class HCPOut(HCPBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Interaction ──────────────────────────────────────────────────────────────

class InteractionBase(BaseModel):
    hcp_id: int
    rep_id: str = "REP-001"
    interaction_type: str = "Meeting"
    interaction_date: Optional[date] = None
    interaction_time: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)
    topics_discussed: Optional[str] = None
    materials_shared: List[str] = Field(default_factory=list)
    samples_distributed: List[str] = Field(default_factory=list)
    products_discussed: List[str] = Field(default_factory=list)
    sentiment: str = "Neutral"
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    summary: Optional[str] = None
    raw_chat_input: Optional[str] = None


class InteractionCreate(InteractionBase):
    pass


class InteractionUpdate(BaseModel):
    hcp_id: Optional[int] = None
    rep_id: Optional[str] = None
    interaction_type: Optional[str] = None
    interaction_date: Optional[date] = None
    interaction_time: Optional[str] = None
    attendees: Optional[List[str]] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[str]] = None
    products_discussed: Optional[List[str]] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    summary: Optional[str] = None


class InteractionOut(InteractionBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    hcp: Optional[HCPOut] = None

    class Config:
        from_attributes = True


# ─── Follow-up ────────────────────────────────────────────────────────────────

class FollowUpCreate(BaseModel):
    hcp_id: int
    interaction_id: Optional[int] = None
    rep_id: str = "REP-001"
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: str = "pending"


class FollowUpOut(FollowUpCreate):
    id: int
    created_at: Optional[datetime] = None
    hcp: Optional[HCPOut] = None

    class Config:
        from_attributes = True


# ─── Agent / Chat ─────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # user | assistant | system
    content: str


class AgentChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    rep_id: str = "REP-001"
    # Optional: pre-selected HCP so agent has context
    hcp_id: Optional[int] = None


class AgentChatResponse(BaseModel):
    reply: str
    form_data: Optional[Dict[str, Any]] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    current_hcp: Optional[Dict[str, Any]] = None
    interaction_id: Optional[int] = None


class SuggestFollowUpsRequest(BaseModel):
    topics_discussed: Optional[str] = None
    outcomes: Optional[str] = None
    hcp_name: Optional[str] = None
    specialty: Optional[str] = None
