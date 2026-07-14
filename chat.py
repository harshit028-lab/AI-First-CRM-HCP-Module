from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..agent.graph import run_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])

# In-memory session store: session_id -> list[BaseMessage]
# Swap for Redis/DB-backed storage in production.
_SESSIONS: dict[str, list] = {}


@router.post("/", response_model=schemas.ChatResponse)
def chat(payload: schemas.ChatMessage, db: Session = Depends(get_db)):
    history = _SESSIONS.get(payload.session_id, [])

    reply, tool_calls, final_messages = run_agent(db, payload.message, history)

    _SESSIONS[payload.session_id] = final_messages[-20:]  # cap context window

    return schemas.ChatResponse(reply=reply, tool_calls=tool_calls)
