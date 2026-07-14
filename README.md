# AI-First CRM — HCP Module: Log Interaction Screen

![React](https://img.shields.io/badge/Frontend-React%20%2B%20Redux-2563eb)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-16a34a)
![LangGraph](https://img.shields.io/badge/Agent-LangGraph-0ea5e9)
![Groq](https://img.shields.io/badge/LLM-Groq-f59e0b)

An AI-first "Log Interaction" screen for a pharma field-rep CRM. Reps can log a
visit with a Healthcare Professional (HCP) either through a **structured form**
or a **conversational chat interface** backed by a **LangGraph agent** running
on **Groq** LLMs — both paths write to the exact same structured database record.

### At a glance

- 🗂️ **Structured form** — precise, click-through logging of HCP visits
- 💬 **AI chat panel** — describe a visit in plain language; the agent extracts and logs it
- 🧠 **LangGraph agent with 5 tools** — `search_hcp`, `log_interaction`, `edit_interaction`, `get_interaction_history`, `suggest_follow_ups`
- ⚡ **Groq-powered** — `gemma2-9b-it` for fast tool routing, `llama-3.3-70b-versatile` for structured entity extraction
- 🗄️ **SQLite by default**, drop-in swap to Postgres/MySQL via one env var

## Why it's designed this way (life-science-expert lens)

Field reps are time-poor and often log notes right after leaving a clinic —
typing a full form isn't realistic in that moment. The chat panel lets a rep
say something like *"Met Dr. Sharma, discussed OncoBoost Phase III data,
positive sentiment, left the brochure and 2 samples"* and have the agent
extract HCP identity, topics, materials, samples, sentiment, and outcomes
automatically, while the structured form stays available for precise edits,
compliance-sensitive fields (e.g. sample chain-of-custody), and reps who
prefer clicking over typing.

## Architecture

```
frontend/  React + Redux Toolkit — Log Interaction Screen (form + chat panel)
backend/
  app/main.py           FastAPI app, CORS, router registration
  app/models.py         SQLAlchemy models: HCP, Interaction, Material, Sample
  app/schemas.py         Pydantic request/response schemas
  app/database.py        SQLAlchemy engine/session (SQLite by default; MySQL/Postgres via DATABASE_URL)
  app/routers/interactions.py   REST CRUD for the structured-form path
  app/routers/chat.py           Drives the LangGraph agent for the chat path
  app/agent/llm.py       Groq client wrapper (gemma2-9b-it default, llama-3.3-70b-versatile for extraction)
  app/agent/tools.py     The 5 LangGraph tools
  app/agent/graph.py     The LangGraph StateGraph (ReAct-style agent loop)
```

## LangGraph Agent

**Role of the agent:** it sits behind the chat panel and turns a rep's
free-text or voice-transcribed note into a structured, persisted interaction
record — resolving the HCP, extracting entities via the LLM, saving the
record, and proactively suggesting follow-ups — so the rep never has to touch
the form for a routine log.

**Graph shape:** `START → agent ⇄ tools → END`, a standard ReAct loop. The
LLM (Groq `gemma2-9b-it`, bound to the 5 tools below via function calling)
either emits a tool call — routed to a `ToolNode` and fed back in — or emits
a final natural-language reply to the rep.

### The 5 tools

| Tool | Purpose |
|---|---|
| `search_hcp` | Resolves an HCP by name/specialty when the rep hasn't already selected one, before any logging happens. |
| `log_interaction` | **(required)** Takes the rep's raw note, calls `llama-3.3-70b-versatile` to extract topics, materials, samples, sentiment, outcomes, and follow-ups as structured JSON, then persists the `Interaction` row. |
| `edit_interaction` | **(required)** Lets the rep amend a single field on an already-logged interaction conversationally (e.g. "actually sentiment was positive"). |
| `get_interaction_history` | Pulls an HCP's most recent past interactions, so the agent (or rep) has context before/after a visit. |
| `suggest_follow_ups` | Generates 2–4 concrete next-best-actions from a logged interaction's content and sentiment. |

`log_interaction`'s use of the LLM for extraction: the raw note is sent to
`extract_entities_and_summary()` (in `agent/llm.py`), which prompts
`llama-3.3-70b-versatile` to return strict JSON matching the interaction
schema. That JSON is merged into the new `Interaction` row before it's
committed — so the same free text that shows up in the chat becomes a fully
structured, queryable database record.

`edit_interaction`'s field update path: it looks the interaction up by id,
validates the field name against the model's actual columns, and applies a
type-appropriate update (e.g. splitting a comma-separated string into a list
for `materials_shared`, parsing JSON for `samples_distributed`), then commits.

## Setup

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your GROQ_API_KEY from console.groq.com/keys
uvicorn app.main:app --reload
```

Runs on `http://localhost:8000`. SQLite is used by default (zero config); set
`DATABASE_URL` in `.env` to point at Postgres or MySQL instead.

### Frontend

```bash
cd frontend
npm install
npm start
```

Runs on `http://localhost:3000` and talks to the backend at
`http://localhost:8000` (override with `REACT_APP_API_BASE`).

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/interactions/` | POST | Log an interaction via the structured form |
| `/api/interactions/{id}` | GET / PATCH | Fetch / edit an interaction |
| `/api/interactions/` | GET | List interactions (optionally filtered by `hcp_id`) |
| `/api/chat/` | POST | Send a chat message; runs the LangGraph agent, returns its reply + tool calls made |

## Notes on the tech choices

- **Groq (`gemma2-9b-it`)** drives the agent's turn-by-turn tool-routing —
  fast and cheap, which matters for a chat UI reps expect to feel instant.
- **`llama-3.3-70b-versatile`** is reserved for the heavier structured-extraction
  step inside `log_interaction`, where accuracy on entity extraction matters
  more than latency.
- **SQLAlchemy** models are written to be dialect-agnostic so the same code
  runs against SQLite (dev), Postgres, or MySQL by swapping `DATABASE_URL`.
- **Redux Toolkit** holds both the structured-form state and the chat
  transcript, so the two logging paths can eventually be reconciled (e.g.
  auto-filling the form from a chat-derived draft) without prop drilling.
