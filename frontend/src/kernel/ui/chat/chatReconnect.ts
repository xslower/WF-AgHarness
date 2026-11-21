
import { streamStore } from "./sessionStore";
import { retryDelay } from "./retryPolicy";
import { pushNotice } from "./reducers";

export interface ReconnectDeps {
  
  pool: { connectWithRetry(sid: string): Promise<unknown> };
  
  hydrate: (sid: string, force?: boolean) => Promise<void>;
}

export class ReconnectManager {
  
  private reconnecting = new Set<string>();
  
  private retryTimers = new Map<string, ReturnType<typeof setTimeout>>();
  
  private retryCount = new Map<string, number>();
  
  private dropped = new Set<string>();

  constructor(private deps: ReconnectDeps) {}

  async reconnect(sid: string): Promise<void> {
    if (this.reconnecting.has(sid)) return;   
    this.reconnecting.add(sid);
    try {
      await this.deps.pool.connectWithRetry(sid);
      this.clearRetry(sid);
      streamStore.patch(sid, {
        live: pushNotice(streamStore.get(sid).live,
          { kind: "notice", text: "✓ 连接已恢复，可继续对话", tag: "reconnect" }),
      });
      
      
      await this.deps.hydrate(sid, true);
    } catch (e) {
      
      
      
      
      this.scheduleRetry(sid, String(e));
    } finally {
      this.reconnecting.delete(sid);
    }
  }

  
  scheduleRetry(sid: string, why = ""): void {
    this.clearRetry(sid);
    const n = (this.retryCount.get(sid) || 0) + 1;
    this.retryCount.set(sid, n);
    const delay = retryDelay(n);
    const t = setTimeout(() => {
      this.retryTimers.delete(sid);
      
      if (!this.knownSid(sid)) return;
      void this.reconnect(sid);
    }, delay);
    (t as unknown as { unref?: () => void }).unref?.();
    this.retryTimers.set(sid, t);
    
    if (n === 1) {
      streamStore.patch(sid, {
        busy: false,
        stopping: false,
        live: pushNotice(streamStore.get(sid).live, {
          kind: "notice",
          text: `连接中断${why ? `（${why.slice(0, 60)}）` : ""}，正在自动重连…`,
          tag: "reconnect",
        }),
      });
    }
  }

  clearRetry(sid: string): void {
    const t = this.retryTimers.get(sid);
    if (t) clearTimeout(t);
    this.retryTimers.delete(sid);
    this.retryCount.delete(sid);
  }

  
  knownSid(sid: string): boolean {
    return !this.dropped.has(sid);
  }

  
  drop(sid: string): void {
    this.reconnecting.delete(sid);
    this.clearRetry(sid);
    this.dropped.add(sid);
  }

  
  revive(sid: string): void {
    this.dropped.delete(sid);
  }

  
  kickReconnects(): void {
    for (const sid of [...this.retryTimers.keys()]) {
      const t = this.retryTimers.get(sid);
      if (t) clearTimeout(t);
      this.retryTimers.delete(sid);
      if (this.knownSid(sid)) void this.reconnect(sid);
    }
  }
}
