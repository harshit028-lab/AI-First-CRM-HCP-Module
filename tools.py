"""
The five LangGraph tools available to the HCP Interaction Agent.

Two are mandated by the assignment spec (log_interaction, edit_interaction);
three more round out a realistic sales-activity toolkit:
  - search_hcp             : look up an HCP by name/specialty before logging
  - suggest_follow_ups     : LLM-generated next-best-actions after a log
  - get_interaction_history: pull an HCP's past interactions for context

Each tool is a plain Python function decorated with @tool so LangGraph's
ToolNode can bind, call, and route on them via the LLM's function-calling.
"""
import json
from datetime import datetime
from typing import Optional

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from .. import models
from .llm import extract_entities_and_summary, chat_completion


# The graph needs a live DB session per-request; we stash it here before
# invoking the agent and clear it after (see graph.py: `with db_session(db)`).
_ACTIVE_DB: Optional[Session] = None


def set_active_db(db: Session):
    global _ACTIVE_DB
    _ACTIVE_DB = db


def _db() -> Session:
    if _ACTIVE_DB is None:
        raise RuntimeError("No active DB session bound. Call set_active_db() first.")
    return _ACTIVE_DB


@tool
def search_hcp(query: str) -> str:
    """Search for a Healthcare Professional (HCP) by name, specialty, or institution.
    Use this before log_interaction if you don't already have a confirmed hcp_id.
    Returns a JSON list of matching HCPs with their id, name, and specialty."""
    db = _db()
    like = f"%{query}%"
    results = (
        db.query(models.HCP)
        .filter(models.HCP.name.ilike(like) | models.HCP.specialty.ilike(like))
        .limit(5)
        .all()
    )
    return json.dumps([
        {"id": h.id, "name": h.name, "specialty": h.specialty, "institution": h.institution}
        for h in results
    ])


@tool
def log_interaction(
    hcp_id: int,
    raw_note: str,
    interaction_type: str = "Meeting",
    logged_via: str = "chat",
) -> str:
    """Log a new HCP interaction from a free-text note (typed or voice-transcribed).
    This tool calls the LLM to extract structured entities from raw_note
    (topics discussed, materials shared, samples distributed, sentiment,
    outcomes, follow-up actions) before persisting the record.
    Returns the created interaction as JSON, including its new id."""
    db = _db()

    extracted = extract_entities_and_summary(raw_note)

    interaction = models.Interaction(
        hcp_id=hcp_id,
        interaction_type=interaction_type,
        interaction_datetime=datetime.utcnow(),
        attendees=[],
        topics_discussed=extracted.get("topics_discussed") or raw_note,
        materials_shared=extracted.get("materials_shared") or [],
        samples_distributed=extracted.get("samples_distributed") or [],
        sentiment=extracted.get("sentiment") or "neutral",
        outcomes=extracted.get("outcomes"),
        follow_up_actions=extracted.get("follow_up_actions"),
        source_note=raw_note,
        logged_via=logged_via,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    return json.dumps({
        "id": interaction.id,
        "hcp_id": interaction.hcp_id,
        "summary": extracted.get("summary"),
        "topics_discussed": interaction.topics_discussed,
        "materials_shared": interaction.materials_shared,
        "samples_distributed": interaction.samples_distributed,
        "sentiment": interaction.sentiment.value if hasattr(interaction.sentiment, "value") else interaction.sentiment,
        "outcomes": interaction.outcomes,
        "follow_up_actions": interaction.follow_up_actions,
    })


@tool
def edit_interaction(interaction_id: int, field: str, new_value: str) -> str:
    """Edit a single field on an already-logged interaction.
    Valid fields: topics_discussed, outcomes, follow_up_actions, sentiment,
    materials_shared (comma-separated string), samples_distributed (JSON list).
    Use this when the rep corrects or amends something after the fact
    (e.g. 'actually sentiment was positive, not neutral').
    Returns the updated interaction as JSON."""
    db = _db()
    interaction = db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
    if not interaction:
        return json.dumps({"error": f"No interaction found with id {interaction_id}"})

    if field == "materials_shared":
        interaction.materials_shared = [m.strip() for m in new_value.split(",") if m.strip()]
    elif field == "samples_distributed":
        try:
            interaction.samples_distributed = json.loads(new_value)
        except json.JSONDecodeError:
            return json.dumps({"error": "samples_distributed must be valid JSON list"})
    elif hasattr(interaction, field):
        setattr(interaction, field, new_value)
    else:
        return json.dumps({"error": f"Unknown field '{field}'"})

    interaction.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(interaction)

    return json.dumps({
        "id": interaction.id,
        "field_updated": field,
        "new_value": new_value,
    })


@tool
def get_interaction_history(hcp_id: int, limit: int = 5) -> str:
    """Retrieve the most recent past interactions logged for a given HCP,
    most recent first. Use this to give the rep context before a visit,
    or to help the agent avoid repeating a follow-up that's already done.
    Returns a JSON list of past interactions."""
    db = _db()
    rows = (
        db.query(models.Interaction)
        .filter(models.Interaction.hcp_id == hcp_id)
        .order_by(models.Interaction.interaction_datetime.desc())
        .limit(limit)
        .all()
    )
    return json.dumps([
        {
            "id": r.id,
            "date": r.interaction_datetime.isoformat() if r.interaction_datetime else None,
            "topics_discussed": r.topics_discussed,
            "sentiment": r.sentiment.value if hasattr(r.sentiment, "value") else r.sentiment,
            "outcomes": r.outcomes,
            "follow_up_actions": r.follow_up_actions,
        }
        for r in rows
    ])


@tool
def suggest_follow_ups(interaction_id: int) -> str:
    """Generate 2-4 AI-suggested next-best-action follow-ups for a logged
    interaction, based on what was discussed, outcomes, and sentiment.
    Returns a JSON list of short follow-up action strings."""
    db = _db()
    interaction = db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
    if not interaction:
        return json.dumps({"error": f"No interaction found with id {interaction_id}"})

    prompt = (
        "Given this HCP interaction, suggest 2-4 short, concrete next-best-action "
        "follow-ups for the field rep (e.g. scheduling, sending materials, adding "
        "to an advisory board). Respond ONLY as a JSON array of strings.\n\n"
        f"Topics discussed: {interaction.topics_discussed}\n"
        f"Outcomes: {interaction.outcomes}\n"
        f"Sentiment: {interaction.sentiment}"
    )
    content = chat_completion(
        messages=[{"role": "user", "content": prompt}],
        model="gemma2-9b-it",
        temperature=0.4,
    )
    try:
        suggestions = json.loads(content)
    except json.JSONDecodeError:
        suggestions = [line.strip("- ") for line in content.splitlines() if line.strip()][:4]
    return json.dumps(suggestions)


ALL_TOOLS = [search_hcp, log_interaction, edit_interaction, get_interaction_history, suggest_follow_ups]
