import React from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  updateField,
  addMaterial,
  addSample,
  setSentiment,
  submitInteractionForm,
} from "../store/interactionSlice";

const SENTIMENTS = [
  { key: "positive", label: "Positive", icon: "🙂" },
  { key: "neutral", label: "Neutral", icon: "😐" },
  { key: "negative", label: "Negative", icon: "🙁" },
];

export default function InteractionForm() {
  const dispatch = useDispatch();
  const { form, status } = useSelector((s) => s.interaction);

  const handle = (field) => (e) =>
    dispatch(updateField({ field, value: e.target.value }));

  return (
    <section className="panel form-panel">
      <h2 className="panel-title">Interaction Details</h2>

      <div className="row two-col">
        <div className="field">
          <label>HCP Name</label>
          <input
            placeholder="Search or select HCP…"
            value={form.hcpName}
            onChange={handle("hcpName")}
          />
        </div>
        <div className="field">
          <label>Interaction Type</label>
          <select value={form.interactionType} onChange={handle("interactionType")}>
            <option>Meeting</option>
            <option>Call</option>
            <option>Email</option>
            <option>Conference</option>
            <option>Sample Drop</option>
          </select>
        </div>
      </div>

      <div className="row two-col">
        <div className="field">
          <label>Date</label>
          <input type="date" value={form.date} onChange={handle("date")} />
        </div>
        <div className="field">
          <label>Time</label>
          <input type="time" value={form.time} onChange={handle("time")} />
        </div>
      </div>

      <div className="field">
        <label>Attendees</label>
        <input
          placeholder="Enter names or search…"
          value={form.attendees.join(", ")}
          onChange={(e) =>
            dispatch(
              updateField({
                field: "attendees",
                value: e.target.value.split(",").map((s) => s.trim()),
              })
            )
          }
        />
      </div>

      <div className="field">
        <label>Topics Discussed</label>
        <textarea
          rows={3}
          placeholder="Enter key discussion points…"
          value={form.topicsDiscussed}
          onChange={handle("topicsDiscussed")}
        />
        <button type="button" className="ghost-btn">
          🎙 Summarize from Voice Note (Requires Consent)
        </button>
      </div>

      <div className="field">
        <label>Materials Shared / Samples Distributed</label>
        <div className="row two-col">
          <div className="mini-card">
            <div className="mini-card-header">
              <span>Materials Shared</span>
              <button
                type="button"
                onClick={() => dispatch(addMaterial(prompt("Material name?") || ""))}
              >
                🔍 Search/Add
              </button>
            </div>
            {form.materialsShared.length === 0 ? (
              <p className="muted">No materials added</p>
            ) : (
              <ul>{form.materialsShared.map((m, i) => <li key={i}>{m}</li>)}</ul>
            )}
          </div>
          <div className="mini-card">
            <div className="mini-card-header">
              <span>Samples Distributed</span>
              <button
                type="button"
                onClick={() =>
                  dispatch(addSample({ name: prompt("Sample name?") || "", qty: 1 }))
                }
              >
                💊 Add Sample
              </button>
            </div>
            {form.samplesDistributed.length === 0 ? (
              <p className="muted">No samples added</p>
            ) : (
              <ul>
                {form.samplesDistributed.map((s, i) => (
                  <li key={i}>{s.name} × {s.qty}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      <div className="field">
        <label>Observed/Inferred HCP Sentiment</label>
        <div className="sentiment-row">
          {SENTIMENTS.map((s) => (
            <label key={s.key} className="sentiment-option">
              <input
                type="radio"
                name="sentiment"
                checked={form.sentiment === s.key}
                onChange={() => dispatch(setSentiment(s.key))}
              />
              {s.icon} {s.label}
            </label>
          ))}
        </div>
      </div>

      <div className="field">
        <label>Outcomes</label>
        <textarea
          rows={2}
          placeholder="Key outcomes or agreements…"
          value={form.outcomes}
          onChange={handle("outcomes")}
        />
      </div>

      <div className="field">
        <label>Follow-up Actions</label>
        <textarea
          rows={2}
          placeholder="Enter next steps or tasks…"
          value={form.followUpActions}
          onChange={handle("followUpActions")}
        />
        {form.aiSuggestedFollowUps.length > 0 && (
          <div className="ai-suggestions">
            <strong>AI Suggested Follow-ups:</strong>
            <ul>
              {form.aiSuggestedFollowUps.map((f, i) => (
                <li key={i}>+ {f}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <button
        className="primary-btn"
        onClick={() => dispatch(submitInteractionForm())}
        disabled={status === "saving"}
      >
        {status === "saving" ? "Saving…" : "Save Interaction"}
      </button>
    </section>
  );
}
