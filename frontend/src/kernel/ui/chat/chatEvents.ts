
import type { SessionStreamState, WsEvent } from "./streamState";
import {
  applyPlan, applySidePanels, applyStreamText, applySubAgent, applyTool,
  applyTurnLifecycle,
} from "./reducers";


export {
  IDLE_PLAN, initialStreamState,
  type LiveEvent, type PlanState, type SessionStreamState,
  type SubAgent, type WsEvent,
} from "./streamState";
export { appendLive, withLastAssistantMeta } from "./reducers";

const GROUPS = [
  applyStreamText,
  applySubAgent,
  applyTool,
  applySidePanels,
  applyTurnLifecycle,
] as const;


export function applyWsEvent(state: SessionStreamState, d: WsEvent): SessionStreamState {
  for (const group of GROUPS) {
    const next = group(state, d);
    if (next !== null) return next;
  }
  
  const planned = applyPlan(state, d, { status: "idle", planText: "" });
  if (planned !== null) return planned;
  return state;
}
