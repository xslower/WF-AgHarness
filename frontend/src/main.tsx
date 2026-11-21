import { migrateLegacyKeys } from "./kernel/chat/chatSessionStore";
import React from "react";
import ReactDOM from "react-dom/client";
import AppShell from "./kernel/app/AppShell";
import { startTimerRunner } from "./kernel/timers/runner";
import "./styles.css";



migrateLegacyKeys();



startTimerRunner();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppShell />
  </React.StrictMode>
);
