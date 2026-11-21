
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../kernel/api";
import type { SubAgentSummary } from "../../kernel/api/domains/subagents";
import type { SubAgent } from "../../kernel/chat/chatTypes";


const PAGE = 100;

const MAX_PAGES = 100;


async function readAll(id: string, parent: string) {
  const messages: unknown[] = [];
  const events: unknown[] = [];
  let offset = 0;
  let status = "done";
  for (let page = 0; page < MAX_PAGES; page++) {
    const d = await api.getSubagent(id, parent, offset, PAGE);
    status = d.status ?? status;
    messages.push(...(d.messages ?? []));
    events.push(...(d.events ?? []));
    const next = d.next_offset;
    if (next === null || next === undefined) break;
    offset = next;
  }
  return { status, messages, events };
}

export interface SubAgentList {
  list: SubAgentSummary[] | null;
  error: string;
  loading: boolean;
  openId: string | null;
  detailOf: (id: string) => SubAgent | undefined;
  reload: () => Promise<void>;
  toggle: (id: string) => Promise<void>;
  close: () => void;
  stop: (id: string) => Promise<void>;
}

export function useSubAgents(sessionId: string, project: string): SubAgentList {
  const [list, setList] = useState<SubAgentSummary[] | null>(null);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);
  
  const [details, setDetails] = useState<Record<string, SubAgent>>({});
  const [loading, setLoading] = useState(false);
  
  const genRef = useRef(0);

  const reload = useCallback(async () => {
    const g = ++genRef.current;
    if (!sessionId) { setList([]); return; }
    try {
      const items = await api.subagentList(sessionId, project);
      if (g !== genRef.current) return;
      setList(Array.isArray(items) ? items : []);
      setError("");
    } catch (e) {
      if (g !== genRef.current) return;
      setError(String((e as Error)?.message ?? e));
    }
  }, [sessionId, project]);

  useEffect(() => { void reload(); }, [reload]);

  const toggle = useCallback(async (id: string) => {
    const closing = openId === id;
    setOpenId(closing ? null : id);
    if (closing || details[id]) return;
    setLoading(true);
    try {
      
      
      
      
      const [detail, result] = await Promise.all([
        readAll(id, sessionId),
        api.subagentResult(id, sessionId).catch(() => null),
      ]);
      const task = list?.find((x) => x.id === id)?.task ?? id;
      setDetails((m) => ({
        ...m,
        [id]: {
          id,
          task,
          status: (detail.status ?? "done") as SubAgent["status"],
          messages: detail.messages,
          events: detail.events as never,
          result: result?.content,
        },
      }));
    } catch {  }
    finally { setLoading(false); }
  }, [details, list, sessionId, openId]);


  const stop = useCallback(async (id: string) => {
    try {
      await api.stopSubagent(id, sessionId);
      await reload();
      setError("");
    } catch (e) {
      
      
      setError(`停止失败：${String((e as Error)?.message ?? e)}`);
    }
  }, [reload, sessionId]);

  const close = useCallback(() => setOpenId(null), []);

  return {
    list, error, loading, openId,
    detailOf: (id: string) => details[id],
    reload, toggle, close, stop,
  };
}
