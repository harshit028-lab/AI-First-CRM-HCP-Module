from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.post("/", response_model=schemas.InteractionOut)
def create_interaction(payload: schemas.InteractionCreate, db: Session = Depends(get_db)):
    """Log an interaction via the structured form (non-AI path)."""
    interaction = models.Interaction(
        hcp_id=payload.hcp_id,
        interaction_type=payload.interaction_type,
        interaction_datetime=payload.interaction_datetime,
        attendees=payload.attendees,
        topics_discussed=payload.topics_discussed,
        materials_shared=payload.materials_shared,
        samples_distributed=[s.dict() for s in payload.samples_distributed],
        sentiment=payload.sentiment,
        outcomes=payload.outcomes,
        follow_up_actions=payload.follow_up_actions,
        source_note=payload.source_note,
        logged_via=payload.logged_via,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


@router.get("/{interaction_id}", response_model=schemas.InteractionOut)
def get_interaction(interaction_id: int, db: Session = Depends(get_db)):
    interaction = db.query(models.Interaction).get(interaction_id)
    if not interaction:
        raise HTTPException(404, "Interaction not found")
    return interaction


@router.patch("/{interaction_id}", response_model=schemas.InteractionOut)
def update_interaction(interaction_id: int, payload: schemas.InteractionUpdate, db: Session = Depends(get_db)):
    interaction = db.query(models.Interaction).get(interaction_id)
    if not interaction:
        raise HTTPException(404, "Interaction not found")
    for field, value in payload.dict(exclude_unset=True).items():
        if field == "samples_distributed" and value is not None:
            value = [s if isinstance(s, dict) else s.dict() for s in value]
        setattr(interaction, field, value)
    db.commit()
    db.refresh(interaction)
    return interaction


@router.get("/", response_model=list[schemas.InteractionOut])
def list_interactions(hcp_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Interaction)
    if hcp_id:
        q = q.filter(models.Interaction.hcp_id == hcp_id)
    return q.order_by(models.Interaction.interaction_datetime.desc()).all()
