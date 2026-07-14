"""
The LangGraph agent that powers the Log Interaction Screen's conversational
side panel.

Role of the agent:
  The rep types free-text like "Met Dr. Sharma, discussed OncoBoost Phase III
  data, positive sentiment, left brochure and 2 samples". The agent decides,
  turn by turn, which tool(s) to call to (a) resolve the HCP if not already
  selected, (b) persist the interaction with extracted structured fields,
  (c) surface AI-suggested follow-ups, and (d) hand back a confirmation the
  UI can render — all without the rep touching the structured form directly.

Graph shape:  START -> agent -> (tools <-> agent)* -> END
  A standard ReAct-style loop: the LLM (bound to our 5 tools) either emits
  tool calls, which are executed and fed back in, or emits a final answer.
"""
import os
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

from .tools import ALL_TOOLS, set_active_db

SYSTEM_PROMPT = """You are the AI assistant embedded in a pharma field rep's \
CRM, on the "Log HCP Interaction" screen. Your job is to let the rep log, \
edit, and review interactions with Healthcare Professionals (HCPs) via \
natural conversation instead of the structured form.

Rules:
- If the rep hasn't specified which HCP, use search_hcp to resolve it before logging.
- Use log_interaction to persist any new interaction described in free text.
- Use edit_interaction when the rep corrects or amends a previously logged interaction.
- Use get_interaction_history when the rep asks about past visits or you need context.
- Use suggest_follow_ups after logging to proactively propose next steps.
- Always confirm back to the rep in plain, concise language what was logged/changed.
- Never fabricate HCP ids or interaction ids — look them up first.
"""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def build_graph():
    llm = ChatGroq(
        model=os.getenv("AGENT_MODEL", "gemma2-9b-it"),
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
    ).bind_tools(ALL_TOOLS)

    def call_model(state: AgentState):
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        response = llm.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState):
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_agent(db_session, user_message: str, history: list | None = None):
    """Bind the DB session, run the graph on the conversation, return the
    final assistant text plus a log of any tool calls made (for the UI/video demo)."""
    from langchain_core.messages import HumanMessage

    set_active_db(db_session)
    graph = get_graph()

    messages = list(history or [])
    messages.append(HumanMessage(content=user_message))

    result = graph.invoke({"messages": messages})
    final_messages = result["messages"]

    tool_calls_made = []
    for m in final_messages:
        if getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                tool_calls_made.append({"tool": tc["name"], "args": tc["args"]})

    reply = final_messages[-1].content
    return reply, tool_calls_made, final_messages
