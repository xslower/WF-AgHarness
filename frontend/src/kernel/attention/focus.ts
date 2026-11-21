
type Listener = () => void;

let current: string | null = null;
const subs = new Set<Listener>();

export function setAttentionFocus(sid: string | null): void {
  const next = sid || null;
  if (current === next) return;
  current = next;
  for (const fn of [...subs]) {
    try { fn(); } catch {  }
  }
}


export function getAttentionFocus(): string | null {
  return current;
}


export function clearAttentionFocus(sid: string | null): void {
  if (!sid || current === sid) setAttentionFocus(null);
}

export function subscribeAttentionFocus(fn: Listener): () => void {
  subs.add(fn);
  return () => { subs.delete(fn); };
}


export function resetAttentionFocusForTest(): void {
  current = null;
  subs.clear();
}
