
import { backendWsUrl } from "./env";

export interface BusEvent {
  seq: number;
  topic: string;
  ts: number;
  payload: Record<string, any>;
}

export type BusHandler = (ev: BusEvent) => void;


export function matchTopic(pattern: string, topic: string): boolean {
  if (pattern === "*" || pattern === topic) return true;
  if (!pattern.includes("*")) return false;
  const a = pattern.split(".");
  const b = topic.split(".");
  if (a.length !== b.length) return false;
  return a.every((seg, i) => seg === "*" || seg === b[i]);
}

interface BridgeOptions {
  
  url?: () => string;
  
  WebSocketImpl?: typeof WebSocket;
}

const MAX_DELAY = 30_000;

const DEAD_AFTER_MS = 90_000;

export class EventBridge {
  private subs = new Map<string, Set<BusHandler>>();
  private reconnectCbs = new Set<() => void>();
  private ws: WebSocket | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  
  private lastSeen = 0;
  
  private watchdog: ReturnType<typeof setInterval> | null = null;
  private attempt = 0;
  private disposed = false;
  private manualClose = false;
  private lifecycleBound = false;
  status: "idle" | "connecting" | "open" | "closed" = "idle";

  constructor(private opts: BridgeOptions = {}) {}

  
  connect(): void {
    if (this.disposed) return;
    if (this.ws && (this.status === "open" || this.status === "connecting")) return;
    this.manualClose = false;
    this.bindLifecycle();
    this.open();
  }

  close(): void {
    this.manualClose = true;
    this.clearTimer();
    this.stopWatchdog();
    try {
      this.ws?.close();
    } catch {
      
    }
    this.ws = null;
    this.status = "closed";
  }

  dispose(): void {
    this.close();
    this.disposed = true;
    this.subs.clear();
    this.reconnectCbs.clear();
  }

  
  on(topic: string, handler: BusHandler): () => void {
    let set = this.subs.get(topic);
    if (!set) {
      set = new Set();
      this.subs.set(topic, set);
    }
    set.add(handler);
    return () => this.off(topic, handler);
  }

  off(topic: string, handler: BusHandler): void {
    const set = this.subs.get(topic);
    if (!set) return;
    set.delete(handler);
    if (!set.size) this.subs.delete(topic);
  }

  
  onReconnect(cb: () => void): () => void {
    this.reconnectCbs.add(cb);
    return () => this.reconnectCbs.delete(cb);
  }

  
  private wsUrl(): string {
    return this.opts.url ? this.opts.url() : backendWsUrl("/ws/events");
  }

  private open(): void {
    const Impl = this.opts.WebSocketImpl
      ?? (typeof WebSocket !== "undefined" ? WebSocket : undefined);
    if (!Impl) return;
    this.status = "connecting";
    let ws: WebSocket;
    try {
      ws = new Impl(this.wsUrl());
    } catch {
      this.status = "closed";
      this.scheduleReconnect();
      return;
    }
    this.ws = ws;
    ws.onopen = () => {
      const wasRetry = this.attempt > 0;
      this.attempt = 0;
      this.status = "open";
      this.lastSeen = Date.now();
      this.startWatchdog();
      if (wasRetry) this.fireReconnect();
    };
    ws.onmessage = (e: MessageEvent) => {
      this.lastSeen = Date.now();   
      let ev: BusEvent;
      try {
        ev = JSON.parse(typeof e.data === "string" ? e.data : "");
      } catch {
        return;
      }
      if (!ev || typeof ev.topic !== "string" || ev.topic.startsWith("sys.")) return;
      this.dispatch(ev);
    };
    ws.onclose = () => {
      if (this.ws === ws) this.ws = null;
      this.status = "closed";
      this.stopWatchdog();
      this.scheduleReconnect();
    };
    ws.onerror = () => {
      try {
        ws.close();
      } catch {
        
      }
    };
  }

  private dispatch(ev: BusEvent): void {
    for (const [pattern, handlers] of this.subs) {
      if (!matchTopic(pattern, ev.topic)) continue;
      for (const h of [...handlers]) {
        try {
          h(ev);
        } catch (err) {
          console.error("[events] handler failed", ev.topic, err);
        }
      }
    }
  }

  private fireReconnect(): void {
    for (const cb of [...this.reconnectCbs]) {
      try {
        cb();
      } catch (err) {
        console.error("[events] reconnect handler failed", err);
      }
    }
  }

  
  private startWatchdog(): void {
    this.stopWatchdog();
    const t = setInterval(() => {
      if (this.status !== "open") return;
      if (Date.now() - this.lastSeen < DEAD_AFTER_MS) return;
      
      try { this.ws?.close(); } catch {  }
    }, 15_000);
    (t as unknown as { unref?: () => void }).unref?.();
    this.watchdog = t;
  }

  private stopWatchdog(): void {
    if (this.watchdog) clearInterval(this.watchdog);
    this.watchdog = null;
  }

  private scheduleReconnect(): void {
    if (this.disposed || this.manualClose) return;
    
    if (typeof document !== "undefined" && document.hidden) return;
    const base = Math.min(MAX_DELAY, 1_000 * 2 ** this.attempt);
    const delay = base * (0.5 + Math.random() * 0.5);
    this.attempt += 1;
    this.clearTimer();
    this.timer = setTimeout(() => this.open(), delay);
  }

  private clearTimer(): void {
    if (this.timer !== null) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }

  private bindLifecycle(): void {
    if (this.lifecycleBound || typeof window === "undefined") return;
    this.lifecycleBound = true;
    
    
    const revive = () => {
      if (this.disposed) return;
      if (this.status !== "open") {
        this.attempt = 0;
        this.clearTimer();
        this.open();
      }
    };
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) revive();
    });
    window.addEventListener("online", revive);
    window.addEventListener("pagehide", () => this.close());
  }
}


export const events = new EventBridge();
