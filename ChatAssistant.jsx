import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { sendChatMessage } from "../store/interactionSlice";

export default function ChatAssistant() {
  const dispatch = useDispatch();
  const { chatMessages } = useSelector((s) => s.interaction);
  const [draft, setDraft] = useState("");

  const send = () => {
    if (!draft.trim()) return;
    dispatch(sendChatMessage(draft.trim()));
    setDraft("");
  };

  return (
    <section className="panel chat-panel">
      <h2 className="panel-title">
        🤖 AI Assistant
        <span className="subtitle">Log interaction via chat</span>
      </h2>

      <div className="chat-log">
        {chatMessages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role}`}>
            {m.text}
          </div>
        ))}
      </div>

      <div className="chat-input-row">
        <input
          placeholder="Describe interaction…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button className="log-btn" onClick={send}>
          ⚡ Log
        </button>
      </div>
    </section>
  );
}
