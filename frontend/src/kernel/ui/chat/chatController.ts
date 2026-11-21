
import { api } from "../../api";
import type { ApprovalItem, SessionDetail } from "../../api";
import { backendWsUrl } from "../../api/env";
import {
  clearPartial, historyOf, lastCtxState, readPartial, savePartial, usageFromDetail,
} from "./chatStorage";
import { dropSession as dropLocalSession } from "../../chat/chatSessionStore";
import { IDLE_PLAN, initialStreamState, type WsEvent } from "./chatEvents";

import { liveFromPartial, shouldRestorePartial, visibleMessages } from "./chatSession";
import { SocketPool } from "./chatSocket";
import { EventCursors, pendingReplay } from "./eventCursor";
import { applyEvent } from "./eventApply";
import { streamStore } from "./sessionStore";
import type { SendOptions, TurnContext } from "./chatTypes";

export type { TurnContext };
import { ReconnectManager } from "./chatReconnect";
import { StreamBuffer, type StreamHooks } from "./chatStreamBuffer";
import { hydrate, refreshSession } from "./chatHydrate";
import { loadOlder, type LoadOlderResult } from "./chatPaging";
import {
  clearDebugLogs, editFrom, queueAction, removeApproval, sendPlanDecision,
  stop as stopAction, type ActionsDeps,
} from "./chatActions";
import {
  messageSubAgent, querySubAgent, setActiveSubAgent, stopSubAgent,
} from "./chatSubAgent";
import { send } from "./chatSend";

export class ChatController {
  private pool: SocketPool;
  
  private focusSid: string | null = null;
  
  private partials = new Map<string, { text: string; reason: string; savedAt: number }>();
  
  private rc!: ReconnectManager;
  
  private cursors = new EventCursors();
  
  
  private stream = new StreamBuffer(() => this.streamHooks());
  
  private attaching = new Set<string>();
  private sessionsChanged = new Set<() => void>();
  private notifyOnDone = false;

  
  constructor(opts?: { wsUrl?: (sid: string) => string; wsFactory?: (url: string) => WebSocket }) {
    this.pool = new SocketPool({
      url: opts?.wsUrl ?? ((sid) => backendWsUrl(`/ws/${sid}`)),
      wsFactory: opts?.wsFactory,
      onMessage: (ev, sid) => this.handleWsEvent(ev, sid),
      onDrop: (sid) => { void this.rc.reconnect(sid); },
    });
    
    this.rc = new ReconnectManager({
      pool: this.pool,
      hydrate: (sid, force) => this.hydrate(sid, force),
    });
  }

  
  private streamHooks(): StreamHooks {
    return {
      buffer: (s) => this.buf(s),
      snapshot: (s) => this.snapshot(s),
      markRunning: (s) => { if (!streamStore.get(s).busy) streamStore.patch(s, { busy: true }); },
      clearRunning: (s) => { streamStore.patch(s, { busy: false, optimisticUntil: 0 }); },
      dropBuffer: (s) => { this.partials.delete(s); },
      fireSessionsChanged: () => this.fireSessionsChanged(),
      refreshSession: (s) => { void this.refreshSession(s); },
      maybeNotify: (s) => this.maybeNotify(s),
    };
  }

  
  private actDeps(): ActionsDeps {
    return {
      socketOf: (sid) => this.pool.socketOf(sid),
      
      
      ensureSocket: (sid) => this.ensureSocket(sid),
    };
  }


  
  
  

  
  onSessionsChanged(fn: () => void): () => void {
    this.sessionsChanged.add(fn);
    return () => { this.sessionsChanged.delete(fn); };
  }

  
  setNotifyOnDone(v: boolean | undefined): void {
    if (typeof v === "boolean") this.notifyOnDone = v;
  }

  
  private fireSessionsChanged(): void {
    for (const fn of [...this.sessionsChanged]) {
      try { fn(); } catch {  }
    }
  }

  
  setFocus(sid: string | null): void {
    this.focusSid = sid;
    if (sid) {
      
      this.reviveSession(sid);
    }
    this.pool.focus(sid);
    if (sid) void this.hydrate(sid);
    this.fireSessionsChanged();
  }

  
  private async ensureSocket(sid: string): Promise<void> {
    if (this.attaching.has(sid)) return;
    if (this.pool.socketOf(sid)) return;
    this.attaching.add(sid);
    try {
      await this.pool.connectWithRetry(sid);
      this.pool.focus(sid);
      
      await this.hydrate(sid, true);
    } catch {
      
    } finally {
      this.attaching.delete(sid);
    }
  }

  isRunning(sid: string): boolean {
    return streamStore.get(sid).busy;
  }

  
  dropSession(sid: string): void {
    this.dropPendingStream(sid);
    dropLocalSession(sid);
    streamStore.drop(sid);
    this.partials.delete(sid);
    this.attaching.delete(sid);
    this.rc.drop(sid);   
  }

  
  reviveSession(sid: string): void {
    this.rc.revive(sid);
  }

  
  
  

  private handleWsEvent(ev: MessageEvent, sid: string): void {
    let d: WsEvent;
    try {
      d = JSON.parse(ev.data) as WsEvent;
    } catch {
      return;  
    }
    
    
    this.cursors.track(sid, d);
    this.handleWsEventData(sid, d);
  }

  
  private queueStream(sid: string, kind: "text" | "reason", text: string): void {
    this.stream.queue(sid, kind, text);
  }

  private flushStream(sid: string): void {
    this.stream.flush(sid);
  }

  private dropPendingStream(sid: string): void {
    this.stream.drop(sid);
  }
  
  private applyReplay(sid: string, items: { i: number; e: Record<string, unknown> }[]): void {
    for (const ev of pendingReplay(items, this.cursors, sid)) {
      this.handleWsEventData(sid, ev);
    }
  }

  
  private handleWsEventData(sid: string, d: WsEvent): void {
    
    
    if (d.type === "text" || d.type === "reason") {
      this.queueStream(sid, d.type, String(d.text ?? d.reason ?? ""));
      return;
    }
    
    
    this.flushStream(sid);
    applyEvent(this.streamHooks(), sid, d);
  }

  private buf(sid: string) {
    let b = this.partials.get(sid);
    if (!b) {
      b = { text: "", reason: "", savedAt: 0 };
      this.partials.set(sid, b);
    }
    return b;
  }

  private snapshot(sid: string): void {
    const b = this.buf(sid);
    const now = Date.now();
    if (now - b.savedAt < 800) return;   
    b.savedAt = now;
    savePartial(sid, { text: b.text, reason: b.reason, ts: now });
  }

  private maybeNotify(sid: string): void {
    if (!this.notifyOnDone || sid === this.focusSid) return;
    if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
    try {
      new Notification("会话已完成", { body: "后台会话跑完了一轮，切过去看看。" });
    } catch {
      
    }
  }

  
  kickReconnects(): void {
    this.rc.kickReconnects();
    
    for (const sid of this.pool.knownSids()) this.pool.poke(sid);
  }

  
  
  
  
  async hydrate(sid: string, force = false): Promise<void> {
    await hydrate(sid, force, {
      cursors: this.cursors,
      flushStream: (s) => this.flushStream(s),
      applyReplay: (s, items) => this.applyReplay(s, items),
      ensureSocket: (s) => this.ensureSocket(s),
    });
  }

  
  async refreshSession(sid: string): Promise<void> {
    await refreshSession(sid);
  }
  
  
  

  loadSession(session: SessionDetail): void {
    const sid = session.id;
    const msgs = visibleMessages(session.messages);
    const todos = Array.isArray(session.todos) ? session.todos : [];
    const ctxState = usageFromDetail(session) ?? lastCtxState(session.messages);
    const logs = historyOf(session.messages);
    
    const msgOffset = session.offset ?? 0;
    const hasMore = !!session.has_more;
    if (!streamStore.has(sid)) {
      
      const partial = readPartial(sid);
      
      
      
      const restore = shouldRestorePartial(msgs, partial);
      if (partial && !restore) clearPartial(sid);
      streamStore.replace(sid, {
        ...initialStreamState(),
        messages: msgs,
        todos,
        debugLogs: logs,
        ctxState,
        msgOffset,
        hasMore,
        live: restore ? liveFromPartial(partial!) : [],
        busy: streamStore.get(sid).busy,
      });
    } else {
      
      
      
      
      
      
      streamStore.patch(sid, { messages: msgs, todos, debugLogs: logs, ctxState,
        msgOffset, hasMore });
    }
    this.setFocus(sid);
    void this.hydrate(sid, true);
  }

  
  reset(): void {
    streamStore.replace("", initialStreamState());
    this.setFocus(null);
  }

  
  
  

  
  async send(ctx: TurnContext, body: string, opts: SendOptions = {}): Promise<boolean> {
    return send({
      pool: this.pool,
      partials: this.partials,
      reviveSession: (s) => this.reviveSession(s),
      setFocus: (s) => this.setFocus(s),
      scheduleRetry: (s, why) => this.rc.scheduleRetry(s, why),
    }, ctx, body, opts);
  }

  

  async stop(sid: string | null): Promise<void> {
    await stopAction(this.actDeps(), sid);
  }

  queueAction(sid: string | null, action: "remove" | "interject" | "cancel_interject",
               id: string): void {
    queueAction(this.actDeps(), sid, action, id);
  }

  sendPlanDecision(sid: string | null, decision: string, feedback?: string,
                   plan?: string): Promise<void> {
    return sendPlanDecision(this.actDeps(), sid, decision, feedback, plan);
  }

  
  removeApproval(sid: string | null, id: string): void {
    removeApproval(sid, id);
  }

  clearDebugLogs(sid: string | null): void {
    clearDebugLogs(sid);
  }

  setActiveSubAgent(sid: string | null, id: string | null): void {
    setActiveSubAgent(sid, id);
  }

  async querySubAgent(sid: string | null, id: string): Promise<void> {
    await querySubAgent(sid, id);
  }

  async messageSubAgent(sid: string | null, id: string, text: string): Promise<boolean> {
    return messageSubAgent(sid, id, text);
  }

  async stopSubAgent(sid: string | null, id: string): Promise<void> {
    await stopSubAgent(sid, id);
  }

  async editFrom(sid: string | null, index: number): Promise<string | null> {
    return editFrom(sid, index);
  }

  
  async loadOlder(sid: string | null): Promise<LoadOlderResult> {
    return loadOlder(sid);
  }
}


export const chatCtl = new ChatController();







if (typeof window !== "undefined") {
  window.addEventListener("online", () => chatCtl.kickReconnects());
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) chatCtl.kickReconnects();
  });
}
