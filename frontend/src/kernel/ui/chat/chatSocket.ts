


const WS_OPEN = 1;


export const MAX_WS_RETRY = 4;


export const HEARTBEAT_MS = 20_000;
export const SOCKET_DEAD_AFTER_MS = 45_000;

export interface SocketPoolDeps {
  url: (sid: string) => string;
  onMessage: (ev: MessageEvent, sid: string) => void;
  
  onDrop: (sid: string) => void;
  
  wsFactory?: (url: string) => WebSocket;
  backoffMs?: number;
}

export class SocketPool {
  private socks = new Map<string, WebSocket>();
  private curWs: WebSocket | null = null;
  private curSid: string | null = null;
  
  private beats = new Map<string, ReturnType<typeof setInterval>>();
  
  private seen = new Map<string, number>();

  constructor(private readonly deps: SocketPoolDeps) {}

  
  get active(): WebSocket | null {
    return this.curWs;
  }

  get activeSid(): string | null {
    return this.curSid;
  }

  
  socketOf(sid: string | null | undefined): WebSocket | null {
    if (!sid) return null;
    const sock = this.socks.get(sid);
    return sock && sock.readyState <= WS_OPEN ? sock : null;
  }

  
  knownSids(): string[] {
    return [...this.socks.keys()];
  }

  
  focus(sid: string | null): void {
    const sock = sid ? this.socks.get(sid) : undefined;
    const alive = sock && sock.readyState <= WS_OPEN ? sock : null;
    this.curSid = alive ? sid : null;
    this.curWs = alive ?? null;
  }

  
  connect(sid: string): Promise<WebSocket> {
    const existing = this.socks.get(sid);
    if (existing && existing.readyState <= WS_OPEN) {
      this.curWs = existing;
      this.curSid = sid;
      return Promise.resolve(existing);
    }
    return new Promise((resolve, reject) => {
      let opened = false;
      const url = this.deps.url(sid);
      const ws = this.deps.wsFactory ? this.deps.wsFactory(url) : new WebSocket(url);
      this.socks.set(sid, ws);
      ws.onopen = () => {
        opened = true;
        this.curWs = ws;
        this.curSid = sid;
        this.seen.set(sid, Date.now());
        this.startHeartbeat(sid, ws);
        resolve(ws);
      };
      ws.onmessage = (ev) => {
        this.seen.set(sid, Date.now());
        this.deps.onMessage(ev, sid);
      };
      ws.onclose = (ev) => {
        this.stopHeartbeat(sid);
        
        if (this.socks.get(sid) === ws) this.socks.delete(sid);
        if (this.curWs === ws) {
          this.curWs = null;
          if (this.curSid === sid) this.curSid = null;
        }
        
        if (!opened) return;
        
        if (ev && ev.code === 4404) return;
        
        
        
        this.deps.onDrop(sid);
      };
      ws.onerror = () => { if (!opened) reject(new Error("WS 连接失败")); };
      this.curWs = ws;
    });
  }

  
  private startHeartbeat(sid: string, ws: WebSocket): void {
    this.stopHeartbeat(sid);
    const timer = setInterval(() => {
      if (this.socks.get(sid) !== ws) { this.stopHeartbeat(sid); return; }
      const hidden = typeof document !== "undefined" && document.hidden;
      const last = this.seen.get(sid) || 0;
      if (!hidden && last && Date.now() - last > SOCKET_DEAD_AFTER_MS) {
        try { ws.close(); } catch {  }
        this.stopHeartbeat(sid);
        return;
      }
      if (ws.readyState === WS_OPEN) {
        try { ws.send(JSON.stringify({ type: "ping" })); } catch {  }
      }
    }, HEARTBEAT_MS);
    
    (timer as unknown as { unref?: () => void }).unref?.();
    this.beats.set(sid, timer);
  }

  
  poke(sid: string): void {
    const ws = this.socks.get(sid);
    if (!ws || ws.readyState !== WS_OPEN) return;
    this.seen.set(sid, Date.now());
    try { ws.send(JSON.stringify({ type: "ping" })); } catch {  }
  }

  private stopHeartbeat(sid: string): void {
    const t = this.beats.get(sid);
    if (t) clearInterval(t);
    this.beats.delete(sid);
  }

  
  dispose(): void {
    for (const sid of [...this.beats.keys()]) this.stopHeartbeat(sid);
    for (const ws of this.socks.values()) {
      try { ws.close(); } catch {  }
    }
    this.socks.clear();
    this.seen.clear();
    this.curWs = null;
    this.curSid = null;
  }

  
  async connectWithRetry(sid: string): Promise<WebSocket> {
    let lastErr: unknown = null;
    const base = this.deps.backoffMs ?? 500;
    for (let i = 0; i < MAX_WS_RETRY; i++) {
      try {
        return await this.connect(sid);
      } catch (e) {
        lastErr = e;
        await new Promise((r) => setTimeout(r, base * 2 ** i));
      }
    }
    throw new Error(`连接失败（已重试 ${MAX_WS_RETRY} 次）：${lastErr}`);
  }
}
