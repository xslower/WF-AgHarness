
import { listSessionIds, readField, writeField } from "../chat/chatSessionStore";

export type SeenMap = Record<string, number>;

export function readSeen(): SeenMap {
  const out: SeenMap = {};
  for (const sid of listSessionIds()) {
    const ts = readField(sid, "seen", 0);
    if (ts > 0) out[sid] = ts;
  }
  return out;
}


export function markSeen(sid: string, at: number): void {
  if (!sid || !(at > 0)) return;
  const prev = readField(sid, "seen", 0);
  if (prev >= at) return;          
  writeField(sid, "seen", at);
}

export function isFresh(
  row: { id: string; running?: boolean; updated_at?: number; message_count?: number },
  seen: SeenMap,
  curId?: string | null,
): boolean {
  if (row.running) return false;
  if (curId && row.id === curId) return false;
  if (!row.message_count) return false;
  const at = row.updated_at || 0;
  return at > (seen[row.id] || 0);
}
