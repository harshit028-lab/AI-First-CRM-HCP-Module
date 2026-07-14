"""
Thin wrapper around Groq's OpenAI-compatible chat completions API.

Models used (per assignment spec):
  - gemma2-9b-it              -> fast, cheap, used for the default agent loop
  - llama-3.3-70b-versatile   -> heavier reasoning, used when the agent needs
                                 to do multi-step entity extraction / summarization

Get a free API key at https://console.groq.com and set GROQ_API_KEY.
"""
import os
from groq import Groq

_client = None


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not set. Create one at https://console.groq.com/keys "
                "and export it before starting the server."
            )
        _client = Groq(api_key=api_key)
    return _client


def chat_completion(messages, model: str = "gemma2-9b-it", temperature: float = 0.2, **kwargs):
    """Call Groq chat completions and return the assistant's text content."""
    client = get_client()
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        **kwargs,
    )
    return resp.choices[0].message.content


def extract_entities_and_summary(raw_text: str) -> dict:
    """
    Use the heavier model (llama-3.3-70b-versatile) to pull structured fields
    out of a free-text / voice-transcribed interaction note.

    Returns a dict matching the InteractionCreate-ish shape so callers can
    merge it straight into the form / DB record.
    """
    import json

    system = (
        "You are a clinical-sales data extraction assistant for a pharma CRM. "
        "Given a field rep's free-text note about a conversation with a healthcare "
        "professional (HCP), extract structured fields. "
        "Respond ONLY with valid JSON, no markdown fences, no commentary, matching this shape:\n"
        '{"hcp_name": string|null, "topics_discussed": string, '
        '"materials_shared": string[], "samples_distributed": [{"name": string, "qty": number}], '
        '"sentiment": "positive"|"neutral"|"negative", "outcomes": string|null, '
        '"follow_up_actions": string|null, "summary": string}'
    )
    content = chat_completion(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": raw_text},
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.0,
    )
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Fall back to a minimal shape if the model didn't return clean JSON
        return {
            "hcp_name": None,
            "topics_discussed": raw_text,
            "materials_shared": [],
            "samples_distributed": [],
            "sentiment": "neutral",
            "outcomes": None,
            "follow_up_actions": None,
            "summary": raw_text[:280],
        }
