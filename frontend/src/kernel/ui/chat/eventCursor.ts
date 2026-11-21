
import type { WsEvent } from "./chatEvents";


export class EventCursors {
  private map = new Map<string, number>();

  
  get(sid: string): number {
    return this.map.get(sid) || 0;
  }

  
  advance(sid: string, seq: number): void {
    if (!Number.isFinite(seq) || seq <= 0) return;
    const cur = this.get(sid);
    if (seq > cur) this.map.set(sid, seq);
  }

  
  track(sid: string, ev: WsEvent): void {
    this.advance(sid, Number(ev._i || 0));
  }

  drop(sid: string): void {
    this.map.delete(sid);
  }
}


const EPHEMERAL = new Set(["notice", "queued", "queue_full"]);


export function pendingReplay(
  items: { i: number; e: Record<string, unknown> }[] | undefined,
  cursors: EventCursors,
  sid: string,
): WsEvent[] {
  const out: WsEvent[] = [];
  if (!items?.length) return out;
  let cur = cursors.get(sid);
  for (const it of items) {
    const seq = Number(it?.i || 0);
    if (!seq || seq <= cur) continue;      
    const ev = it.e as WsEvent;
    if (!ev || typeof ev !== "object") continue;
    cur = seq;                            
    if (EPHEMERAL.has(String(ev.type || ""))) continue;
    if (ev._i !== seq) ev._i = seq;        
    out.push(ev);
  }
  cursors.advance(sid, cur);
  return out;
}
