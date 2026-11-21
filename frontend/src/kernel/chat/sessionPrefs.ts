
import { NEW_SESSION_KEY, readField, writeField } from "./chatSessionStore";

export { NEW_SESSION_KEY };


export interface SessionPrefs {
  
  model?: string;
  
  workflow?: string;
  
  plan?: string;
  
  policy?: string;
}

type Store = Record<string, unknown>;

export function readPrefs(sid: string | null | undefined): SessionPrefs {
  return readField(sid, "prefs", {}) as SessionPrefs;
}

export function writePrefs(sid: string | null | undefined, prefs: SessionPrefs): void {
  writeField(sid, "prefs", prefs as Store);
}

export function patchPrefs(sid: string | null | undefined, patch: SessionPrefs): SessionPrefs {
  const next = { ...readPrefs(sid), ...patch };
  writePrefs(sid, next);
  return next;
}


export function dropPrefs(sid: string | null | undefined): void {
  writeField(sid, "prefs", undefined);
}


export function readPolicyPref(sid: string | null | undefined): string {
  return (readPrefs(sid).policy || "").trim();
}

export function writePolicyPref(sid: string | null | undefined, mode: string): SessionPrefs {
  return patchPrefs(sid, { policy: mode });
}


export function specStillValid(
  spec: string,
  config: { providers?: { name?: string; models?: { id: string; disabled?: boolean }[] }[];
            queues?: { parent?: string[]; child?: string[]; summary?: string[] } } | null,
): boolean {
  const s = (spec ?? "").trim() || "parent";
  if (!config) return true;                    
  if (s === "child") return (config.queues?.child ?? []).length > 0;
  if (s === "summary") {
    const q = config.queues ?? {};
    return (q.summary ?? []).length > 0 || (q.child ?? []).length > 0
      || (q.parent ?? []).length > 0;
  }
  if (s === "parent") return true;
  return (config.providers ?? []).some(
    (p) => p.models?.some((m) => `${p.name}/${m.id}` === s && !m.disabled));
}
