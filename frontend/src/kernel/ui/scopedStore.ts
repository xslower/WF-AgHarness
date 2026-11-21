
import { readSession, writeField } from "../chat/chatSessionStore";


export const SCOPE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

const PREFIX = "ui.scope.";
const TTL_PREFIX = "ui.scopeTtl.";

export interface ScopedRecord<T> {
  v: T;
  t: number;
}


function sessionSid(scope: string): string | null {
  return scope.startsWith("sess:") ? scope.slice(5) : null;
}

function wfKeyOf(scope: string, name: string): string {
  return `${PREFIX}${scope}:${name}`;
}


function readSessionScope<T>(sid: string, name: string, ttl: number): T | undefined {
  const sc = readSession(sid).scope ?? {};
  const rec = sc[name] as ScopedRecord<T> | undefined;
  if (!rec || typeof rec !== "object" || !("v" in rec)) return undefined;
  if (Date.now() - (Number(rec.t) || 0) > ttl) {
    delete sc[name];
    writeField(sid, "scope", sc);
    return undefined;
  }
  return rec.v;
}


function writeSessionScope<T>(sid: string, name: string, value: T): void {
  const sc = readSession(sid).scope ?? {};
  sc[name] = { v: value, t: Date.now() } as { v: unknown; t: number };
  writeField(sid, "scope", sc);
}

function readWf<T>(scope: string, name: string, ttl: number): T | undefined {
  try {
    const raw = localStorage.getItem(wfKeyOf(scope, name));
    if (!raw) return undefined;
    const rec = JSON.parse(raw) as ScopedRecord<T>;
    if (!rec || typeof rec !== "object" || !("v" in rec)) return undefined;
    if (Date.now() - (Number(rec.t) || 0) > ttl) {
      localStorage.removeItem(wfKeyOf(scope, name));
      return undefined;
    }
    return rec.v;
  } catch {
    return undefined;
  }
}

function writeWf<T>(scope: string, name: string, value: T, ttl: number): void {
  try {
    const rec: ScopedRecord<T> = { v: value, t: Date.now() };
    localStorage.setItem(wfKeyOf(scope, name), JSON.stringify(rec));
    localStorage.setItem(TTL_PREFIX + scope, String(Date.now() + ttl));
  } catch {
    
  }
}
export const scopedStore = {
  read<T>(scope: string, name: string, ttl: number): T | undefined {
    const sid = sessionSid(scope);
    return sid ? readSessionScope<T>(sid, name, ttl) : readWf<T>(scope, name, ttl);
  },

  write<T>(scope: string, name: string, value: T, ttl: number): void {
    const sid = sessionSid(scope);
    if (sid) writeSessionScope(sid, name, value);
    else writeWf(scope, name, value, ttl);
  },

  
  clearScope(scope: string): void {
    const sid = sessionSid(scope);
    if (sid) { writeField(sid, "scope", undefined); return; }
    try {
      const prefix = `${PREFIX}${scope}:`;
      const dead: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && k.startsWith(prefix)) dead.push(k);
      }
      dead.forEach((k) => localStorage.removeItem(k));
      localStorage.removeItem(TTL_PREFIX + scope);
    } catch {
      
    }
  },

  
  prune(aliveScopes?: Set<string>): number {
    let removed = 0;
    try {
      const now = Date.now();
      const dead: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (!k || !k.startsWith(PREFIX)) continue;
        const rest = k.slice(PREFIX.length);
        if (rest.startsWith("sess:")) continue;      
        const sep = rest.lastIndexOf(":");
        if (sep <= 0) { dead.push(k); continue; }
        let expired = false;
        try {
          const rec = JSON.parse(localStorage.getItem(k) || "null") as ScopedRecord<unknown> | null;
          expired = now > (Number(rec?.t) || 0) + SCOPE_TTL_MS;
        } catch { expired = true; }
        const scope = rest.slice(0, sep);
        const gone = aliveScopes ? !aliveScopes.has(scope) : false;
        if (expired || gone) dead.push(k);
      }
      dead.forEach((k) => { localStorage.removeItem(k); removed++; });
    } catch {
      
    }
    return removed;
  },
};
