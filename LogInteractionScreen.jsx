import React from "react";
import InteractionForm from "./InteractionForm";
import ChatAssistant from "./ChatAssistant";

export default function LogInteractionScreen() {
  return (
    <div className="screen">
      <header className="screen-header">
        <h1>Log HCP Interaction</h1>
      </header>
      <div className="screen-body">
        <InteractionForm />
        <ChatAssistant />
      </div>
    </div>
  );
}
