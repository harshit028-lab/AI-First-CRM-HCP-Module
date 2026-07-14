import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

const emptyForm = {
  hcpId: null,
  hcpName: "",
  interactionType: "Meeting",
  date: new Date().toISOString().slice(0, 10),
  time: new Date().toTimeString().slice(0, 5),
  attendees: [],
  topicsDiscussed: "",
  materialsShared: [],
  samplesDistributed: [],
  sentiment: "neutral",
  outcomes: "",
  followUpActions: "",
  aiSuggestedFollowUps: [],
};

export const submitInteractionForm = createAsyncThunk(
  "interaction/submitForm",
  async (_, { getState }) => {
    const { form } = getState().interaction;
    const res = await fetch(`${API_BASE}/api/interactions/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        hcp_id: form.hcpId,
        interaction_type: form.interactionType,
        interaction_datetime: `${form.date}T${form.time}:00`,
        attendees: form.attendees,
        topics_discussed: form.topicsDiscussed,
        materials_shared: form.materialsShared,
        samples_distributed: form.samplesDistributed,
        sentiment: form.sentiment,
        outcomes: form.outcomes,
        follow_up_actions: form.followUpActions,
        logged_via: "form",
      }),
    });
    if (!res.ok) throw new Error("Failed to save interaction");
    return res.json();
  }
);

export const sendChatMessage = createAsyncThunk(
  "interaction/sendChatMessage",
  async (message, { getState }) => {
    const { sessionId } = getState().interaction;
    const res = await fetch(`${API_BASE}/api/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
    if (!res.ok) throw new Error("Chat request failed");
    return res.json();
  }
);

const interactionSlice = createSlice({
  name: "interaction",
  initialState: {
    form: emptyForm,
    chatMessages: [
      {
        role: "assistant",
        text: 'Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure") or ask for help.',
      },
    ],
    sessionId: `session-${Date.now()}`,
    status: "idle",
    error: null,
  },
  reducers: {
    updateField(state, action) {
      const { field, value } = action.payload;
      state.form[field] = value;
    },
    addMaterial(state, action) {
      state.form.materialsShared.push(action.payload);
    },
    addSample(state, action) {
      state.form.samplesDistributed.push(action.payload);
    },
    setSentiment(state, action) {
      state.form.sentiment = action.payload;
    },
    resetForm(state) {
      state.form = { ...emptyForm, date: new Date().toISOString().slice(0, 10) };
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(submitInteractionForm.pending, (state) => {
        state.status = "saving";
      })
      .addCase(submitInteractionForm.fulfilled, (state) => {
        state.status = "saved";
      })
      .addCase(submitInteractionForm.rejected, (state, action) => {
        state.status = "error";
        state.error = action.error.message;
      })
      .addCase(sendChatMessage.pending, (state, action) => {
        state.chatMessages.push({ role: "user", text: action.meta.arg });
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.chatMessages.push({ role: "assistant", text: action.payload.reply });
        if (action.payload.tool_calls?.length) {
          const usedFollowUpTool = action.payload.tool_calls.find(
            (t) => t.tool === "suggest_follow_ups"
          );
          if (usedFollowUpTool) {
            // Follow-ups come back inside the assistant reply text in this
            // simple wiring; a richer UI could parse tool_calls results directly.
          }
        }
      })
      .addCase(sendChatMessage.rejected, (state, action) => {
        state.chatMessages.push({
          role: "assistant",
          text: `Sorry, something went wrong: ${action.error.message}`,
        });
      });
  },
});

export const { updateField, addMaterial, addSample, setSentiment, resetForm } =
  interactionSlice.actions;
export default interactionSlice.reducer;
