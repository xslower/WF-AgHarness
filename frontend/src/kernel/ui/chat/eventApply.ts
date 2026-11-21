
import { clearPartial, clearSentInput } from "./chatStorage";
import type { WsEvent } from "./chatEvents";
import { streamStore } from "./sessionStore";
import { releasePlanDecision } from "./chatActions";

export interface EventApplyDeps {
  
  buffer: (sid: string) => { text: string; reason: string; savedAt: number };
  
  snapshot: (sid: string) => void;
  
  markRunning: (sid: string) => void;
  clearRunning: (sid: string) => void;
  
  dropBuffer: (sid: string) => void;
  
  fireSessionsChanged: () => void;
  
  refreshSession: (sid: string) => void;
  
  maybeNotify: (sid: string) => void;
}


export function applyEvent(deps: EventApplyDeps, sid: string, d: WsEvent): void {
  sideEffectsBefore(deps, sid, d);
  
  streamStore.apply(sid, d);
  afterApply(deps, sid, d);
}


function sideEffectsBefore(deps: EventApplyDeps, sid: string, d: WsEvent): void {
  if (d.type === "text") {
    deps.buffer(sid).text += String(d.text || "");
    deps.snapshot(sid);
    return;
  }
  if (d.type === "reason") {
    deps.buffer(sid).reason += String(d.reason ?? d.text ?? "");
    deps.snapshot(sid);
    return;
  }
  if (d.type === "done" || d.type === "error") {
    
    deps.dropBuffer(sid);
    clearPartial(sid);
    return;
  }
  if (d.type === "turn_start") {
    
    
    
    deps.markRunning(sid);
    
    
    deps.fireSessionsChanged();
  }
}


function afterApply(deps: EventApplyDeps, sid: string, d: WsEvent): void {
  
  
  if (d.type === "plan_approved" || d.type === "plan_modify"
      || d.type === "plan_cancelled" || d.type === "plan_ready") {
    releasePlanDecision(sid);
  }
  if (d.type === "done") {
    
    
    clearSentInput(sid);
    deps.clearRunning(sid);
    deps.fireSessionsChanged();
    deps.maybeNotify(sid);
    return;
  }
  if (d.type === "turn_saved") {
    
    
    clearSentInput(sid);
    void deps.refreshSession(sid);
    return;
  }
  if (d.type === "error") {
    deps.clearRunning(sid);
    deps.fireSessionsChanged();
    
    
    void deps.refreshSession(sid);
  }
}
