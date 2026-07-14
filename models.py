"""
SQLAlchemy ORM models for the AI-First CRM HCP module.

Works with either MySQL or PostgreSQL — the connection string in database.py
decides which driver is used; these model definitions are dialect-agnostic.
"""
from datetime import datetime
import enum

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship

from .database import Base


class SentimentEnum(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class InteractionTypeEnum(str, enum.Enum):
    meeting = "Meeting"
    call = "Call"
    email = "Email"
    conference = "Conference"
    sample_drop = "Sample Drop"


class HCP(Base):
    """A Healthcare Professional the field rep engages with."""
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    specialty = Column(String(255), nullable=True)
    institution = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    advisory_board_member = Column(String(10), default="No")

    interactions = relationship("Interaction", back_populates="hcp")


class Interaction(Base):
    """A single logged interaction with an HCP — the core record of this module."""
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id"), nullable=False)

    interaction_type = Column(Enum(InteractionTypeEnum), default=InteractionTypeEnum.meeting)
    interaction_datetime = Column(DateTime, default=datetime.utcnow)

    attendees = Column(JSON, default=list)  # list[str]
    topics_discussed = Column(Text, nullable=True)

    materials_shared = Column(JSON, default=list)   # list[str] material names/ids
    samples_distributed = Column(JSON, default=list)  # list[{"name": str, "qty": int}]

    sentiment = Column(Enum(SentimentEnum), default=SentimentEnum.neutral)
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)

    # raw free-text the rep typed/spoke, kept for audit + re-summarization
    source_note = Column(Text, nullable=True)
    logged_via = Column(String(20), default="form")  # "form" | "chat" | "voice"

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")


class Material(Base):
    """Marketing / clinical materials that can be shared with an HCP."""
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)  # e.g. "Brochure", "Clinical Study"


class Sample(Base):
    """Drug/product samples that can be distributed to an HCP."""
    __tablename__ = "samples"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    lot_number = Column(String(100), nullable=True)
