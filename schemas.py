from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class SampleItem(BaseModel):
    name: str
    qty: int = 1


class InteractionBase(BaseModel):
    hcp_id: int
    interaction_type: str = "Meeting"
    interaction_datetime: Optional[datetime] = None
    attendees: List[str] = []
    topics_discussed: Optional[str] = None
    materials_shared: List[str] = []
    samples_distributed: List[SampleItem] = []
    sentiment: str = "neutral"
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    source_note: Optional[str] = None
    logged_via: str = "form"


class InteractionCreate(InteractionBase):
    pass


class InteractionUpdate(BaseModel):
    interaction_type: Optional[str] = None
    interaction_datetime: Optional[datetime] = None
    attendees: Optional[List[str]] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[SampleItem]] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


class InteractionOut(InteractionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    session_id: str
    message: str
    hcp_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    tool_calls: List[Dict[str, Any]] = []
    interaction: Optional[InteractionOut] = None
