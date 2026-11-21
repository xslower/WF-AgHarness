
import type { ApprovalItem, ChatMessage, SessionDetail, TodoItem } from "../../api";
import type { DebugLog } from "./chatStorage";
import type { LiveEvent, PlanState, SubAgent } from "./chatEvents";
import type { QueueItem } from "./queueOps";

export interface SendOptions {
  images?: string[];
  audio?: string;
  attachments?: { name: string; text: string }[];
  
  workflow?: string;
  
  plan?: boolean;
}


export interface TurnContext {
  sid: string | null;
  project: string;
  model: string;
  
  policy?: string;
  sessionMeta?: { kind?: string; origin?: string };
  
  onSessionCreated?: (id: string) => void;
}

export interface ChatStreamOptions {
  project: string;
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
  refreshSessions: () => Promise<void>;
  modelSel: string;
  
  sessionMeta?: { kind?: string; origin?: string };
  
  notifyOnDone?: boolean;
}

export interface ChatStream {
  messages: ChatMessage[];
  live: LiveEvent[];
  busy: boolean;
  
  activeSpec: string;
  ctxState: { used: number; model: string } | null;
  suggestions: string[];
  debugLogs: DebugLog[];
  subAgents: Record<string, SubAgent>;
  activeSubAgent: string | null;
  setActiveSubAgent: (id: string | null) => void;
  pendingApprovals: ApprovalItem[];
  removeApproval: (id: string) => void;
  todos: TodoItem[];
  planState: PlanState;
  
  sendPlanDecision: (decision: string, feedback?: string, plan?: string) => Promise<void>;
  clearDebugLogs: () => void;
  send: (body: string, options?: SendOptions) => Promise<boolean>;
  stop: () => Promise<void>;
  stopping: boolean;
  
  queue: QueueItem[];
  queueAction: (action: "remove" | "interject" | "cancel_interject", id: string) => void;
  querySubAgent: (id: string) => Promise<void>;
  messageSubAgent: (id: string, text: string) => Promise<boolean>;
  stopSubAgent: (id: string) => Promise<void>;
  loadSession: (session: SessionDetail) => void;
  reset: () => void;
  
  dropSession: (sid: string) => void;
  editFrom: (index: number) => Promise<string | null>;
  
  loadOlder: () => Promise<{ added: boolean; count: number }>;
  
  hasMore: boolean;
  
  msgOffset: number;
  
}
