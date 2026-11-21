
import type { ApprovalItem, ChatMessage, TodoItem } from "../api";

export interface LiveEvent {
  
  kind: "text" | "notice" | "tool" | "error" | "reason" | "subagent";
  text: string;
  toolName?: string;
  args?: unknown;
  result?: string;
  
  output?: string;
  
  subagentId?: string;
  
  wfRunId?: string;
  
  tag?: "partial" | "reconnect";
}

export interface SubAgent {
  id: string;
  task: string;
  status: "running" | "done" | "failed" | "stopped";
  result?: string;
  resultPath?: string;
  error?: string;
  messages?: unknown[];
  events?: { type?: string; text?: string; name?: string }[];
}

export interface PlanState {
  status: "idle" | "planning" | "awaiting_approval" | "executing" | "cancelled";
  planText: string;
}


export interface WsEvent {
  type?: string;
  [key: string]: unknown;
}


export interface DebugLog {
  event: string;
  round?: number;
  model?: string;
  usage?: { prompt_tokens: number; completion_tokens: number } | null;
  has_tool_calls?: boolean;
  tool_calls?: unknown;
  text_preview?: string;
  reasoning?: string;
  message_count?: number;
  last_user_msg?: string;
  [key: string]: unknown;
}


export const MAX_QUEUE = 3;

export interface QueueItem {
  id: string;
  content: string;
  
  images: number;
  
  attachments: string[];
  workflow: string;
  
  interjecting: boolean;
}


export interface SessionStreamState {
  messages: ChatMessage[];
  live: LiveEvent[];
  
  busy: boolean;
  
  optimisticUntil: number;
  
  stopping: boolean;
  
  ctxState: { used: number; model: string; estimated?: boolean } | null;
  suggestions: string[];
  debugLogs: DebugLog[];
  subAgents: Record<string, SubAgent>;
  pendingApprovals: ApprovalItem[];
  todos: TodoItem[];
  planState: PlanState;
  queue: QueueItem[];
  
  activeSubAgent: string | null;
  
  syncedAt: number;
  
  msgOffset: number;
  
  hasMore: boolean;
  
  activeSpec: string;
}

export const IDLE_PLAN: PlanState = { status: "idle", planText: "" };

export function initialStreamState(): SessionStreamState {
  return {
    messages: [],
    live: [],
    busy: false,
    optimisticUntil: 0,
    stopping: false,
    ctxState: null,
    suggestions: [],
    debugLogs: [],
    subAgents: {},
    pendingApprovals: [],
    todos: [],
    planState: IDLE_PLAN,
    queue: [],
    activeSubAgent: null,
    activeSpec: "",
    syncedAt: 0,
    msgOffset: 0,
    hasMore: false,
  };
}
