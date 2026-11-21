
import { api } from "../../api";
import type { SessionLive } from "../../api";
import { IDLE_PLAN } from "./chatEvents";
import { visibleMessages } from "./chatSession";
import { lastCtxState, usageFromDetail } from "./chatStorage";
import { mergeStream } from "./chatSession";
import { mergeWindow } from "./windowMerge";
import type { EventCursors } from "./eventCursor";
import type { QueueItem } from "./queueOps";
import { streamStore } from "./sessionStore";


export function toQueueItem(it: SessionLive["queue"][number]): QueueItem {
  return {
    id: it.id,
    content: it.content,
    images: 0,
    attachments: [],
    workflow: "",
    interjecting: !!it.interjecting,
  };
}

export interface HydrateDeps {
  cursors: EventCursors;
  
  flushStream: (sid: string) => void;
  
  applyReplay: (sid: string, items: { i: number; e: Record<string, unknown> }[]) => void;
  
  ensureSocket: (sid: string) => Promise<void>;
}

export async function hydrate(sid: string, force: boolean, deps: HydrateDeps): Promise<void> {
  if (!sid) return;
  
  
  deps.flushStream(sid);
  const cur = streamStore.get(sid);
  if (!force && cur.syncedAt && Date.now() - cur.syncedAt < 1500) return;
  try {
    
    
    const since = deps.cursors.get(sid);
    const live = await api.sessionLive(sid, since);
    
    
    if (live.replay?.length) {
      deps.applyReplay(sid, live.replay);
    }
    
    
    const prev = streamStore.get(sid);
    
    deps.cursors.advance(sid, Number(live.lastSeq || 0));
    const status = live.plan?.status ?? "idle";
    const planText = live.plan?.planText ?? "";
    
    
    
    
    const optimistic = prev.optimisticUntil > Date.now();
    const backendRunning = !!live.running;
    
    
    
    
    const nextLive = mergeStream(prev.live, live.stream);
    
    
    
    const remoteQueue = live.queue.map(toQueueItem);
    const localById = new Map(prev.queue.map((q) => [q.id, q]));
    const mergedQueue = remoteQueue.map((q) => {
      const local = localById.get(q.id);
      if (local && local.content.length > q.content.length) {
        return { ...q, content: local.content };
      }
      return q;
    });
    streamStore.patch(sid, {
      
      
      busy: backendRunning || optimistic,
      optimisticUntil: optimistic && !backendRunning ? prev.optimisticUntil : 0,
      queue: mergedQueue,
      planState: status === "idle" && !planText ? IDLE_PLAN : { status, planText },
      
      
      ctxState: usageFromDetail(live) ?? (live.usage ? prev.ctxState : null),
      todos: live.todos ?? [],
      pendingApprovals: (live.approvals ?? []) as unknown as never[],
      ...(nextLive !== prev.live ? { live: nextLive } : {}),
      syncedAt: Date.now(),
    });
    
    
    
    
    
    const needsAnswer = backendRunning
      || status === "awaiting_approval"
      || (live.approvals ?? []).length > 0;
    if (needsAnswer) void deps.ensureSocket(sid);
  } catch {
    
  }
}


export async function refreshSession(sid: string): Promise<void> {
  if (!sid || !streamStore.has(sid)) return;
  try {
    const s = await api.getSession(sid);
    const prev = streamStore.get(sid);
    
    
    
    const w = mergeWindow(
      { messages: prev.messages, offset: prev.msgOffset },
      { messages: visibleMessages(s.messages), offset: s.offset ?? 0 },
      !!s.has_more);
    streamStore.patch(sid, {
      messages: w.messages,
      msgOffset: w.offset,
      hasMore: w.hasMore,
      todos: Array.isArray(s.todos) ? s.todos : [],
      
      
      ctxState: usageFromDetail(s) ?? lastCtxState(s.messages) ?? prev.ctxState,
      
      
      
      ...(prev.busy ? {} : { live: prev.live.filter((e) => e.kind === "error") }),
    });
  } catch {
    
  }
}


