


export const NEW_SESSION_KEY = "__new__";


export function viewScope(sid: string | null | undefined): string {
  return `sess:${sid || NEW_SESSION_KEY}`;
}

export interface ChatSessionRecord {
  
  prefs?: Record<string, unknown>;
  
  partial?: Record<string, unknown>;
  
  input?: { v: string; ts: number; sent?: boolean };
  
  scroll?: number;
  
  planAuto?: Record<string, unknown>;
  
  scope?: Record<string, { v: unknown; t: number }>;
  
  seen?: number;
  
  lastSid?: string;
}

const PREFIX = "chat.";

const LEGACY_DOTTED = ["draft.", "partial."];


export function keyOf(sid: string | null | undefined): string {
  return PREFIX + (sid || NEW_SESSION_KEY);
}

function readRecord(sid: string | null | undefined): ChatSessionRecord {
  try {
    const raw = localStorage.getItem(keyOf(sid));
    if (!raw) return {};
    const v = JSON.parse(raw) as unknown;
    return v && typeof v === "object" && !Array.isArray(v)
      ? v as ChatSessionRecord : {};
  } catch {
    return {};                       
  }
}


function writeRecord(sid: string | null | undefined, rec: ChatSessionRecord): boolean {
  try {
    localStorage.setItem(keyOf(sid), JSON.stringify(rec));
    return true;
  } catch {
    
    return false;
  }
}


export function readField<K extends keyof ChatSessionRecord>(
  sid: string | null | undefined, name: K, fallback: NonNullable<ChatSessionRecord[K]>,
): NonNullable<ChatSessionRecord[K]> {
  const v = readRecord(sid)[name];
  return (v === undefined || v === null ? fallback : v) as NonNullable<ChatSessionRecord[K]>;
}


export function writeFieldOk<K extends keyof ChatSessionRecord>(
  sid: string | null | undefined, name: K, value: ChatSessionRecord[K] | undefined,
): boolean {
  const rec = readRecord(sid);
  if (value === undefined) delete rec[name];
  else rec[name] = value;
  return writeRecord(sid, rec);
}


export function writeField<K extends keyof ChatSessionRecord>(
  sid: string | null | undefined, name: K, value: ChatSessionRecord[K] | undefined,
): void {
  writeFieldOk(sid, name, value);
}


export function readSession(sid: string | null | undefined): ChatSessionRecord {
  return readRecord(sid);
}


export function initSession(sid: string | null | undefined): void {
  const key = keyOf(sid);
  try {
    if (localStorage.getItem(key) === null) localStorage.setItem(key, "{}");
  } catch {  }
}


export function resetNewSessionSlot(): void {
  const rec = readRecord(NEW_SESSION_KEY);
  for (const f of ["prefs", "input", "planAuto", "partial", "scroll"] as const) {
    delete rec[f];
  }
  const key = keyOf(NEW_SESSION_KEY);
  try {
    if (Object.keys(rec).length) localStorage.setItem(key, JSON.stringify(rec));
    else localStorage.removeItem(key);
  } catch {  }
}


export function dropSession(sid: string | null | undefined): void {
  try { localStorage.removeItem(keyOf(sid)); } catch {  }
}


export function listSessionIds(): string[] {
  try {
    const out: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (!k || !k.startsWith(PREFIX)) continue;
      const sid = k.slice(PREFIX.length);
      if (sid === NEW_SESSION_KEY || LEGACY_DOTTED.some((p) => sid.startsWith(p))) continue;
      out.push(sid);
    }
    return out;
  } catch { return []; }
}


export function pruneOrphans(alive: Set<string>): number {
  let removed = 0;
  for (const sid of listSessionIds()) {
    if (alive.has(sid)) continue;
    dropSession(sid);
    removed++;
  }
  return removed;
}



interface LegacyKey {
  prefix: string;
  
  perSid: boolean;
  field: keyof ChatSessionRecord;
  pick?: (entry: unknown) => unknown;
}

const LEGACY: LegacyKey[] = [
  { prefix: "ui.prefs.", perSid: true, field: "prefs" },
  
  { prefix: "chat.draft.", perSid: true, field: "input", pick: () => undefined },
  { prefix: "chat.partial.", perSid: true, field: "partial" },
  { prefix: "ui.planAuto.", perSid: true, field: "planAuto" },
  { prefix: "ui.inputs", perSid: false, field: "input",
    pick: (e) => e && typeof e === "object" ? e : undefined },
  { prefix: "ui.seen", perSid: false, field: "seen",
    pick: (e) => typeof e === "number" ? e
      : (e && typeof e === "object" && typeof (e as { ts?: number }).ts === "number")
        ? (e as { ts: number }).ts : undefined },
];

function parse(raw: string | null): unknown {
  if (!raw) return undefined;
  try { return JSON.parse(raw) as unknown; } catch { return undefined; }
}


function move(sid: string, field: keyof ChatSessionRecord, v: unknown): boolean {
  if (v === undefined) return false;
  const rec = readRecord(sid);
  if (rec[field] !== undefined) return false;
  rec[field] = v as never;
  writeRecord(sid, rec);
  return true;
}


export function migrateLegacyKeys(): number {
  let moved = 0;
  try {
    for (const { prefix, perSid, field, pick } of LEGACY) {
      if (perSid) {
        const keys: string[] = [];
        for (let i = 0; i < localStorage.length; i++) {
          const k = localStorage.key(i);
          if (k && k.startsWith(prefix)) keys.push(k);
        }
        for (const k of keys) {
          const raw = parse(localStorage.getItem(k));
          
          
          if (move(k.slice(prefix.length), field, pick ? pick(raw) : raw)) moved++;
          localStorage.removeItem(k);
        }
      } else {
        const m = parse(localStorage.getItem(prefix));
        if (m && typeof m === "object") {
          for (const [sid, entry] of Object.entries(m as Record<string, unknown>)) {
            if (move(sid, field, pick ? pick(entry) : entry)) moved++;
          }
        }
        localStorage.removeItem(prefix);
      }
    }
    
    const scrollKeys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith("ui.scroll.")) scrollKeys.push(k);
    }
    for (const k of scrollKeys) {
      const n = Number(localStorage.getItem(k));
      if (Number.isFinite(n) && n > 0 && move(k.slice("ui.scroll.".length), "scroll", n)) moved++;
      localStorage.removeItem(k);
    }
    
    const scopeKeys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith("ui.scope.sess:")) scopeKeys.push(k);
    }
    for (const k of scopeKeys) {
      const rest = k.slice("ui.scope.sess:".length);
      
      const sep = rest.indexOf(":");
      if (sep <= 0) { localStorage.removeItem(k); continue; }
      const sid = rest.slice(0, sep);
      const name = rest.slice(sep + 1);
      const v = parse(localStorage.getItem(k));
      if (v && typeof v === "object") {
        const rec = readRecord(sid);
        const sc = (rec.scope ?? {}) as Record<string, { v: unknown; t: number }>;
        if (sc[name] === undefined) {
          sc[name] = v as { v: unknown; t: number };
          writeField(sid, "scope", sc);
          moved++;
        }
      }
      localStorage.removeItem(k);
      localStorage.removeItem("ui.scopeTtl.sess:" + sid);
    }
  } catch {
    
  }
  return moved;
}
