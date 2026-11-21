
import type { ApprovalItem, ChatMessage, TodoItem } from "../../api";
import type { DebugLog } from "./chatStorage";
import type { QueueItem } from "./queueOps";
import type { LiveEvent, PlanState, SessionStreamState, SubAgent, WsEvent } from "./streamState";

const str = (v: unknown): string => (v === null || v === undefined ? "" : String(v));

  
export function appendLive(live: LiveEvent[], kind: "text" | "reason", text: string): LiveEvent[] {
  const last = live[live.length - 1];
  if (last?.kind === kind) return [...live.slice(0, -1), { kind, text: last.text + text }];
  return [...live, { kind, text }];
}


export function pushNotice(live: LiveEvent[], e: LiveEvent): LiveEvent[] {
  if (e.tag === "reconnect") {
    
    return [...live.filter((x) => x.tag !== "reconnect"), e];
  }
  return [...live, e];
}


export function clearRoundTransients(live: LiveEvent[]): LiveEvent[] {
  if (!live.some((e) => e.kind === "notice" || e.kind === "error")) return live;
  return live.filter((e) => e.kind !== "notice" && e.kind !== "error");
}


function patchTool(
  live: LiveEvent[],
  match: (item: LiveEvent) => boolean,
  patch: (item: LiveEvent) => LiveEvent,
): LiveEvent[] {
  for (let i = live.length - 1; i >= 0; i--) {
    if (live[i].kind === "tool" && match(live[i])) {
      const cp = [...live];
      cp[i] = patch(cp[i]);
      return cp;
    }
  }
  return live;
}


function subagentFailed(result: unknown): boolean {
  return !(result && typeof result === "string" && !result.includes("error"));
}



export function withLastAssistantMeta(
  messages: ChatMessage[],
  meta: { ts?: unknown; usage_total?: unknown; cost?: unknown },
): ChatMessage[] {
  let i = -1;
  for (let k = messages.length - 1; k >= 0; k--) {
    if (messages[k].role === "assistant") { i = k; break; }
  }
  if (i < 0) return messages;
  const cp = [...messages];
  cp[i] = { ...cp[i], ...meta } as ChatMessage;
  return cp;
}


export function applyStreamText(state: SessionStreamState, d: WsEvent): SessionStreamState | null {
  switch (d.type) {
    case "text":
      return { ...state, live: appendLive(state.live, "text", str(d.text)) };
    case "reason":
      return { ...state, live: appendLive(state.live, "reason", str(d.text)) };
    case "model":
      
      return { ...state, activeSpec: str(d.spec) };
    case "notice":
    case "queued":
      return { ...state, live: pushNotice(state.live,
        { kind: "notice", text: str(d.text || d.type) }) };
    case "queue_full":
      return { ...state, live: [...state.live, { kind: "error", text: str(d.text || "队列已满") }] };
    default:
      return null;
  }
}



export function applySubAgent(state: SessionStreamState, d: WsEvent): SessionStreamState | null {
  const id = str(d.subagent_id);
  switch (d.type) {
    case "subagent_start": {
      
      const already = state.live.some((e) => e.kind === "subagent" && e.subagentId === id);
      return {
        ...state,
        subAgents: {
          ...state.subAgents,
          [id]: {
            id,
            task: str(d.task || "子任务"),
            status: "running",
            messages: [],
            events: [],
          },
        },
        live: already ? state.live
          : [...state.live, { kind: "subagent", text: "", subagentId: id }],
      };
    }

    case "subagent_event": {
      const cur = state.subAgents[id];
      if (!cur) return state;
      const events = [...(cur.events ?? []), d.event as { type?: string; text?: string; name?: string }];
      
      return {
        ...state,
        subAgents: { ...state.subAgents, [id]: { ...cur, events: events.slice(-200) } },
      };
    }

    case "subagent_done": {
      const cur = state.subAgents[id];
      if (!cur) return state;
      return {
        ...state,
        subAgents: {
          ...state.subAgents,
          [id]: {
            ...cur,
            status: d.status as SubAgent["status"],
            resultPath: d.result_path as string | undefined,
            error: d.error as string | undefined,
          },
        },
      };
    }
    default:
      return null;
  }
}


export function applyTool(state: SessionStreamState, d: WsEvent): SessionStreamState | null {
  switch (d.type) {
    case "tool_start":
      
      
      return {
        ...state,
        live: [...state.live, {
          kind: "tool", text: "", toolName: str(d.name), args: d.args,
        }],
      };

    case "tool_output":
      
      return {
        ...state,
        live: patchTool(state.live, (it) => !it.result, (it) => ({
          ...it,
          
          output: ((it.output || "") + str(d.text)).slice(-20000),
        })),
      };

    case "workflow_run": {
      
      
      const rid = str(d.run_id);
      if (!rid) return state;
      return {
        ...state,
        live: patchTool(state.live, (it) => it.toolName === "workflow",
          (it) => ({ ...it, wfRunId: rid })),
      };
    }

    case "tool_end":
      return applyToolEnd(state, d);
    default:
      return null;
  }
}


function applyToolEnd(state: SessionStreamState, d: WsEvent): SessionStreamState {
  const live = patchTool(
    state.live,
    (it) => !it.result && it.toolName === d.name,
    (it) => ({ ...it, args: d.args, result: d.result as string | undefined }),
  );
  
  let subAction = "";
  if (d.name === "subagent") {
    try { subAction = str(JSON.parse(str(d.args || "{}")).action || "spawn"); }
    catch { subAction = "spawn"; }
  }
  if (subAction !== "spawn") return { ...state, live };
  const running = Object.values(state.subAgents).filter((x) => x.status === "running");
  if (running.length === 0) return { ...state, live };
  const target = running[running.length - 1];
  return {
    ...state,
    live,
    subAgents: {
      ...state.subAgents,
      [target.id]: {
        ...target,
        status: subagentFailed(d.result) ? "failed" : "done",
        result: str(d.result),
      },
    },
  };
}


export function applyPlan(state: SessionStreamState, d: WsEvent, idle: PlanState): SessionStreamState | null {
  switch (d.type) {
    case "plan_start":
      return { ...state, planState: { status: "planning", planText: "" } };
    case "plan_ready":
      
      return { ...state, planState: { status: "awaiting_approval", planText: str(d.text) } };
    case "plan_approved":
      return { ...state, planState: { ...state.planState, status: "executing" } };
    case "plan_modify":
      return { ...state, planState: { status: "planning", planText: "" } };
    case "plan_cancelled":
      return { ...state, planState: idle };
    default:
      return null;
  }
}


export function applySidePanels(state: SessionStreamState, d: WsEvent): SessionStreamState | null {
  switch (d.type) {
    case "approval_request":
      return { ...state, pendingApprovals: [...state.pendingApprovals, d as unknown as ApprovalItem] };
    case "approval_done":
      return { ...state, pendingApprovals: state.pendingApprovals.filter((x) => x.id !== d.id) };
    case "todo":
      return { ...state, todos: Array.isArray(d.todos) ? (d.todos as TodoItem[]) : [] };
    case "suggestions":
      return { ...state, suggestions: Array.isArray(d.items) ? (d.items as string[]) : [] };
    case "debug":
      return { ...state, debugLogs: [...state.debugLogs, d.debug as DebugLog] };
    case "queue":
      return { ...state, queue: Array.isArray(d.items) ? (d.items as QueueItem[]) : [] };
    default:
      return null;
  }
}


export function applyTurnLifecycle(state: SessionStreamState, d: WsEvent): SessionStreamState | null {
  switch (d.type) {
    case "turn_start":
      return applyTurnStart(state, d);
    case "ctx_estimate":
      return applyCtxEstimate(state, d);
    case "done":
      return applyDone(state, d);
    case "error":
      return applyError(state, d);
    default:
      return null;
  }
}


function applyTurnStart(state: SessionStreamState, d: WsEvent): SessionStreamState {
  
  const next: SessionStreamState = { ...state, busy: true, live: clearRoundTransients(state.live) };
  
  
  if (d.from_queue && d.id && state.queue.some((q) => q.id === d.id)) {
    next.queue = state.queue.filter((q) => q.id !== d.id);
  }
  return next;
}


function applyCtxEstimate(state: SessionStreamState, d: WsEvent): SessionStreamState {
  const used = Number(d.used);
  
  
  if (!Number.isFinite(used) || used <= 0) return state;
  return { ...state,
           ctxState: { used, model: str(d.model) || state.ctxState?.model || "",
                       estimated: true } };
}


function applyDone(state: SessionStreamState, d: WsEvent): SessionStreamState {
  const next: SessionStreamState = {
    ...state,
    stopping: false,
    
    busy: state.queue.length > 0,
  };
  
  
  
  if (state.live.some((e) => e.kind === "notice" || e.kind === "subagent" || e.tag === "partial")) {
    next.live = state.live.filter((e) => e.kind !== "notice" && e.kind !== "subagent"
      && e.tag !== "partial");
  }
  if (d.usage) {
    const u = d.usage as { prompt_tokens: number; completion_tokens: number };
    const used = (u.prompt_tokens || 0) + (u.completion_tokens || 0);
    
    
    if (used > 0) {
      next.ctxState = {
        used,
        model: str(d.model) || state.ctxState?.model || "",
        estimated: false,     
      };
    }
  }
  return next;
}


function applyError(state: SessionStreamState, d: WsEvent): SessionStreamState {
  return {
    ...state,
    live: [...state.live, { kind: "error", text: str(d.text) }],
    busy: false,
    stopping: false,
  };
}
