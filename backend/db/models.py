from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from db.database import Base


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    specialty = Column(String(150), nullable=True)
    hospital = Column(String(200), nullable=True)
    location = Column(String(150), nullable=True)
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="hcp")
    follow_ups = relationship("FollowUp", back_populates="hcp")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id"), nullable=False, index=True)
    rep_id = Column(String(100), nullable=False, default="REP-001")
    interaction_type = Column(String(50), nullable=False, default="Meeting")
    interaction_date = Column(Date, nullable=False, default=date.today)
    interaction_time = Column(String(20), nullable=True)
    attendees = Column(JSON, default=list)  # list of names
    topics_discussed = Column(Text, nullable=True)
    materials_shared = Column(JSON, default=list)  # list of strings
    samples_distributed = Column(JSON, default=list)  # list of strings
    products_discussed = Column(JSON, default=list)
    sentiment = Column(String(50), default="Neutral")  # Positive / Neutral / Negative
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)  # LLM-generated summary
    raw_chat_input = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")
    follow_ups = relationship("FollowUp", back_populates="interaction")


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id"), nullable=False, index=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id"), nullable=True)
    rep_id = Column(String(100), nullable=False, default="REP-001")
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String(50), default="pending")  # pending / completed / cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

    hcp = relationship("HCP", back_populates="follow_ups")
    interaction = relationship("Interaction", back_populates="follow_ups")
