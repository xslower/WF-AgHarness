
import {
  applyWsEvent,
  initialStreamState,
  type SessionStreamState,
  type WsEvent,
} from "./chatEvents";


const EMPTY: SessionStreamState = Object.freeze(initialStreamState()) as SessionStreamState;

export class SessionStreamStore {
  private map = new Map<string, SessionStreamState>();
  private subs = new Map<string, Set<() => void>>();

  
  get(sid: string | null | undefined): SessionStreamState {
    return this.map.get(sid ?? "") ?? EMPTY;
  }

  
  has(sid: string | null | undefined): boolean {
    return this.map.has(sid ?? "");
  }

  
  apply(sid: string, ev: WsEvent): boolean {
    const key = sid || "";
    const prev = this.get(key);
    const next = applyWsEvent(prev, ev);
    if (next === prev) return false;
    this.commit(key, next);
    return true;
  }

  
  patch(sid: string, partial: Partial<SessionStreamState>): void {
    const key = sid || "";
    this.commit(key, { ...this.get(key), ...partial });
  }

  
  replace(sid: string, state: SessionStreamState): void {
    this.commit(sid || "", state);
  }

  
  ensure(sid: string): SessionStreamState {
    const key = sid || "";
    const cur = this.map.get(key);
    if (cur) return cur;
    const fresh = initialStreamState();
    this.map.set(key, fresh);
    return fresh;
  }

  subscribe(sid: string | null | undefined, fn: () => void): () => void {
    const key = sid ?? "";
    let set = this.subs.get(key);
    if (!set) {
      set = new Set();
      this.subs.set(key, set);
    }
    set.add(fn);
    return () => {
      const s = this.subs.get(key);
      if (!s) return;
      s.delete(fn);
      if (s.size === 0) this.subs.delete(key);
    };
  }

  
  drop(sid: string): void {
    const key = sid || "";
    this.map.delete(key);
    this.subs.delete(key);
  }

  
  snapshotAll(): Map<string, SessionStreamState> {
    return new Map(this.map);
  }

  
  clear(): void {
    this.map.clear();
    this.subs.clear();
  }

  private commit(key: string, next: SessionStreamState): void {
    this.map.set(key, next);
    const set = this.subs.get(key);
    if (!set) return;
    for (const fn of [...set]) {
      try {
        fn();
      } catch {
        
      }
    }
  }
}


export const streamStore = new SessionStreamStore();


export function resetStreamStoreForTest(): void {
  streamStore.clear();
}
