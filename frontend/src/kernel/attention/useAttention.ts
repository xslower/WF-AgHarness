
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { api } from "../api";
import type { AttentionSnapshot, SessionAttentionRow } from "../api";
import { events } from "../api/eventBridge";
import { flowAttn, hasAny, sessionAttn, type Attn } from "./attn";
import { EMPTY_ATTN } from "./attn";
import { getAttentionFocus, subscribeAttentionFocus } from "./focus";
import { isFresh, markSeen, readSeen, type SeenMap } from "./seen";

const EMPTY_SNAP: AttentionSnapshot = { sessions: [], workflows: [] };

const COALESCE_MS = 250;

const POLL_MS = 30_000;

export interface AttentionApi {
  snapshot: AttentionSnapshot;
  seen: SeenMap;
  
  of: (sid: string) => Attn;
  
  ofFlow: (project: string, name: string) => Attn;
  
  refresh: () => Promise<void>;
  
  hasWaiting: boolean;
  
  markSidSeen: (sid: string) => void;
}

export function useAttention(curId?: string | null): AttentionApi {
  
  
  const focusSid = useSyncExternalStore(
    subscribeAttentionFocus, getAttentionFocus, getAttentionFocus);
  const watching = focusSid || curId || null;
  const [snapshot, setSnapshot] = useState<AttentionSnapshot>(EMPTY_SNAP);
  const [seen, setSeen] = useState<SeenMap>(() => readSeen());
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  const snapshotRef = useRef<AttentionSnapshot>(EMPTY_SNAP);
  snapshotRef.current = snapshot;
  
  const alive = useRef(true);

  const load = useCallback(async () => {
    try {
      const d = await api.attention();
      if (alive.current) setSnapshot(d);
    } catch {
      
    }
  }, []);

  const refresh = useCallback(async () => {
    await load();
  }, [load]);

  
  const schedule = useCallback(() => {
    if (timer.current) return;
    timer.current = setTimeout(() => {
      timer.current = null;
      void load();
    }, COALESCE_MS);
  }, [load]);

  useEffect(() => {
    alive.current = true;
    void load();

    const offs = [
      events.on("session.attention", () => schedule()),
      
      events.on("workflow.run", () => schedule()),
      
      events.onReconnect(() => { void load(); }),
    ];
    const poll = setInterval(() => { void load(); }, POLL_MS);

    return () => {
      alive.current = false;
      for (const off of offs) off();
      clearInterval(poll);
      if (timer.current) { clearTimeout(timer.current); timer.current = null; }
    };
  }, [load, schedule]);

  
  
  useEffect(() => {
    if (!watching) return;
    const row = snapshot.sessions.find((r) => r.id === watching);
    if (!row) return;
    markSeen(watching, row.updated_at || 0);
    setSeen((prev) => {
      const at = row.updated_at || 0;
      if ((prev[watching] || 0) >= at) return prev;   
      return { ...prev, [watching]: at };
    });
  }, [snapshot, watching]);

  
  const markSidSeen = useCallback((sid: string) => {
    if (!sid) return;
    const row = snapshotRef.current.sessions.find((r) => r.id === sid);
    const at = row?.updated_at || 0;
    if (!(at > 0)) return;
    markSeen(sid, at);
    setSeen((prev) => ((prev[sid] || 0) >= at ? prev : { ...prev, [sid]: at }));
  }, []);

  const byId = useMemo(() => {
    const m = new Map<string, SessionAttentionRow>();
    for (const r of snapshot.sessions) m.set(r.id, r);
    return m;
  }, [snapshot]);

  const of = useCallback(
    (sid: string) => sessionAttn(byId.get(sid), seen, watching),
    [byId, seen, watching],
  );

  const ofFlow = useCallback(
    (project: string, name: string) =>
      flowAttn(snapshot.sessions, snapshot.workflows, project, name, seen, watching),
    [snapshot, seen, watching],
  );

  const hasWaiting = useMemo(
    () => snapshot.sessions.some((r) => r.approvals > 0 || r.plan)
      || snapshot.workflows.length > 0,
    [snapshot],
  );

  return { snapshot, seen, of, ofFlow, refresh, hasWaiting, markSidSeen };
}

export { EMPTY_ATTN, hasAny, isFresh };
export type { Attn };
