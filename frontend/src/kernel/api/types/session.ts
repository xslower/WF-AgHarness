

import type { ApprovalItem } from "./misc";


export interface SessionSummary {
  id: string;
  title: string;
  project: string;
  created_at: number;
  message_count: number;
  
  kind?: string;
  
  origin?: string;
  
  running?: boolean;
  
  queued?: number;
}



export interface SessionAttentionRow {
  id: string;
  title: string;
  project: string;
  
  kind: string;
  origin: string;
  message_count: number;
  
  running: boolean;
  
  queued: number;
  
  approvals: number;
  
  plan: boolean;
  
  updated_at: number;
}



export interface PendingHumanItem {
  project: string;
  
  workflow: string;
  
  sub_workflow?: string;
  run: string;
  node: string;
  title: string;
  ask: string;
  options: string[];
  created: number;
  scope: "workflow" | "global";
}



export interface AttentionSnapshot {
  sessions: SessionAttentionRow[];
  workflows: PendingHumanItem[];
}



export interface SessionLive {
  sid: string;
  running: boolean;
  queue: { id: string; content: string; interjecting: boolean }[];
  plan: { status: "idle" | "planning" | "awaiting_approval" | "executing" | "cancelled";
          planText: string };
  
  usage: { used: number; model: string; estimated?: boolean } | null;
  todos: TodoItem[];
  approvals: ApprovalItem[];
  
  
  draft?: ChatMessage[];
  
  stream?: { text: string; reason: string };
  
  replay?: { i: number; e: Record<string, unknown> }[];
  
  lastSeq?: number;
  ts?: number;
}

export interface PromptPreset {
  id: string;
  name: string;
  description: string;
  prefix: string;
  suffix: string;
}

export interface SubAgentPlaceholder {
  id: string;
  task: string;
  status: "running" | "done" | "failed";
  result?: string;
  messages?: ChatMessage[];
}

export interface ProjectNode {
  name: string;
  path: string;
  depth: number;
  children: ProjectNode[];
  
  pluginProject?: boolean;
  devMode?: boolean;
  pluginId?: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "tool" | "system";
  content: string | { type: string; text?: string; image_url?: { url: string } }[] | null;
  tool_calls?: { id: string; function: { name: string; arguments: string } }[];
  tool_call_id?: string;
  model?: string;
  usage?: { prompt_tokens: number; completion_tokens: number } | null;
  
  usage_total?: { prompt_tokens: number; completion_tokens: number } | null;
  
  cost?: number;
  
  ts?: number;
  reasoning?: string;
  
  _sys?: string;
  
  _bg_job?: string;
}

export interface TodoItem {
  content: string;
  status: "pending" | "in_progress" | "done";
}

export interface SessionDetail {
  id: string;
  title: string;
  project: string;
  messages: ChatMessage[];
  kind?: string;
  origin?: string;
  
  todos?: TodoItem[];
  
  total?: number;
  
  offset?: number;
  
  has_more?: boolean;
  
  usage?: { used: number; model: string; estimated?: boolean } | null;
}


