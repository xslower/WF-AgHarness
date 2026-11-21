
import { applyEvent } from "./eventApply";
import type { WsEvent } from "./chatEvents";


export const STREAM_FLUSH_MS = 50;

interface Pending {
  
  segs: { kind: "text" | "reason"; text: string }[];
  timer: ReturnType<typeof setTimeout> | null;
}


export type StreamHooks = Parameters<typeof applyEvent>[0];

export class StreamBuffer {
  private pending = new Map<string, Pending>();

  constructor(private hooks: () => StreamHooks) {}

  
  queue(sid: string, kind: "text" | "reason", text: string): void {
    if (!text) return;
    let q = this.pending.get(sid);
    if (!q) {
      q = { segs: [], timer: null };
      this.pending.set(sid, q);
    }
    
    const last = q.segs[q.segs.length - 1];
    if (last && last.kind === kind) last.text += text;
    else q.segs.push({ kind, text });
    if (q.timer !== null) return;
    const t = setTimeout(() => this.flush(sid), STREAM_FLUSH_MS);
    (t as unknown as { unref?: () => void }).unref?.();
    q.timer = t;
  }

  
  flush(sid: string): void {
    const q = this.pending.get(sid);
    if (!q) return;
    if (q.timer !== null) { clearTimeout(q.timer); q.timer = null; }
    const segs = q.segs;
    q.segs = [];
    if (!segs.length) return;
    
    for (const seg of segs) {
      applyEvent(this.hooks(), sid, { type: seg.kind, text: seg.text } as WsEvent);
    }
  }

  
  drop(sid: string): void {
    const q = this.pending.get(sid);
    if (!q) return;
    if (q.timer !== null) clearTimeout(q.timer);
    this.pending.delete(sid);
  }
}
